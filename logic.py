#!/usr/bin/env pypy
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
from itertools import count
from collections import OrderedDict, namedtuple
from graficaS import *

path_file_debug = "/home/andrea/Scrivania/DEBUG-CHESS/"
# The table size is the maximum number of elements in the transposition table.
TABLE_SIZE = 1e6

# This constant controls how much time we spend on looking for optimal moves.
NODES_SEARCHED = 1e3


# Mate value must be greater than 8*queen + 2*(rook+knight+bishop)
# King value is set to twice this value such that if the opponent is
# 8 queens up, but we got the king, we still exceed MATE_VALUE.
MATE_VALUE = 99999999#30000

# posizioni border della mia scacchiera in coordinate = interi
A1, H1, A8, H8 = 91, 98, 21, 28    #stanno a significare i posti in valori numerici

# confgurazione di inizio --> solo il Re nelle rispettive prime file e tutti i pedoni nelle seconde
config_iniziale = (
    '         \n'  #   0 -  9
    '         \n'  #  10 - 19
    ' ....k...\n'  #  20 - 29
    ' pppppppp\n'  #  30 - 39
    ' ........\n'  #  40 - 49
    ' ........\n'  #  50 - 59
    ' ........\n'  #  60 - 69
    ' ........\n'  #  70 - 79
    ' PPPPPPPP\n'  #  80 - 89
    ' ....K...\n'  #  90 - 99
    '         \n'  # 100 -109
    '          '   # 110 -119
)

# tabella delle direzioni che pedone e re possono assumere
N, E, S, W = -10, 1, 10, -1
directions = {
    'P': (N, 2*N, N+W, N+E),
    'K': (N, E, S, W, N+E, S+E, S+W, N+W)
}

# tabella di valutazione scacchi
pst = {
    'P': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 198, 198, 198, 198, 198, 198, 198, 198, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 178, 198, 208, 218, 218, 208, 198, 178, 0,
        0, 178, 198, 218, 238, 238, 218, 198, 178, 0,
        0, 178, 198, 208, 218, 218, 208, 198, 178, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 198, 198, 198, 198, 198, 198, 198, 198, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'K': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 60098, 60132, 60073, 60025, 60025, 60073, 60132, 60098, 0,
        0, 60119, 60153, 60094, 60046, 60046, 60094, 60153, 60119, 0,
        0, 60146, 60180, 60121, 60073, 60073, 60121, 60180, 60146, 0,
        0, 60173, 60207, 60148, 60100, 60100, 60148, 60207, 60173, 0,
        0, 60196, 60230, 60171, 60123, 60123, 60171, 60230, 60196, 0,
        0, 60224, 60258, 60199, 60151, 60151, 60199, 60258, 60224, 0,
        0, 60287, 60321, 60262, 60214, 60214, 60262, 60321, 60287, 0,
        0, 60298, 60332, 60273, 60225, 60225, 60273, 60332, 60298, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
}

###############################################################################
# Chess logic
###############################################################################

file_mosse = open(path_file_debug+"tracemosse.txt","w")
file_mossa_migl = open(path_file_debug+"tracemossemigliori.txt","w")
file_aggiorno_migliore = open(path_file_debug+"aggiornomigliori.txt","w")

class Position(namedtuple('Position', 'board score wc bc ep kp')):
    """ A state of a chess game
    board -- a 120 char representation of the board
    score -- the board evaluation
    wc -- the castling rights
    bc -- the opponent castling rights
    ep - the en passant square
    kp - the king passant square
    """
    #genera tutte le mosse che un giocatore puo effettuare di tutti i pezzi di un giocatore
    def genMoves(self):
        # controllo se sono sotto scacco..
        scacco = self.sotto_scacco()
        # per tutti i pezzi
        for i, p in enumerate(self.board):
            # se il pezzo è maiuscolo continuo perchè sto considerando i miei pezzi
            if not p.isupper(): continue
            # considero tutte le direzioni in cui può andare il pezzo, sia esso pedone o re
            for d in directions[p]:
                for j in count(i+d, d):
                    # se il pezzo è un pedone e sono in una situazione di scacco non considero le sue mosse tra le
                    # possibili perchè penso a mettere in sicuro il re
                    if (p == 'P' and scacco): break
                    # prendo il pezzo nella posizione j
                    q = self.board[j]
                    # se è uno spazio non lo considero
                    if self.board[j].isspace(): break
                    # Non mangio i miei pezzi
                    if q.isupper(): break
                    # gestione di movimento dei pedoni in avanti, avanti di due, diagonale
                    if p == 'P' and d in (N+W, N+E) and q == '.' : break
                    if p == 'P' and d in (N, 2*N) and q != '.': break
                    # solo nelle posizioni 81/88(quelle iniziali) puoi muovere il pedone di 2 in verticale
                    if p == 'P' and d == 2*N and (i < A1+N or self.board[i+N] != '.'): break
                    # posizioni sottoscacco di pedone se ci vado
                    if p == 'K' and (self.board[j-11] == 'p' or self.board[j-9] == 'p'): break
                    # posizione sottoscacco di re se ci vado (i re non possono stare vicini ne mangiarsi)
                    if p == 'K' and (self.board[j-11] == 'k'): break    #N+W
                    if p == 'K' and (self.board[j-9] == 'k'): break     #N+E
                    if p == 'K' and (self.board[j-10] == 'k'): break    #N
                    if p == 'K' and (self.board[j-1] == 'k'): break     #W
                    if p == 'K' and (self.board[j+1] == 'k'): break     #E
                    if p == 'K' and (self.board[j+9] == 'k'): break     #S+W
                    if p == 'K' and (self.board[j+10] == 'k'): break    #S
                    if p == 'K' and (self.board[j+11] == 'k'): break    #S+E
                    # Aggiungi mossa
                    yield (i, j)
                    # Stop crawlers from sliding
                    if p in ('P', 'K'): break
                    # No sliding after captures
                    if q.islower(): break

    # funzione che determina se la tabella è in una condizione di scacco
    def sotto_scacco(self):
    # controllo che non si sia in una situazione di scacco
        for i, p in enumerate(self.board):
            # sono sotto scacco se un pedone è nella cella diagonale(sx o dx) al re, è l'unico modo per avere uno scacco se si
            # hanno solo pedoni
            if (p == 'K') and (self.board[i-11] == 'p' or self.board[i-9] == 'p'):
                return True
        return False

    # rotazione della scacchiera
    def rotate(self):
        return Position(
            self.board[::-1].swapcase(), -self.score,
            self.bc, self.wc, 119-self.ep, 119-self.kp)

    # effettua la mossa, aggiorna score e torna la nuova tabella aggiornata
    def move(self, move):
        # i casella iniziale della mossa move, j casella in cui ci si intende muovere
        i, j = move
        #
        p, q = self.board[i], self.board[j]
        put = lambda board, i, p: board[:i] + p + board[i+1:]
        # Copy variables and reset ep and kp
        board = self.board
        wc, bc, ep, kp = self.wc, self.bc, 0, 0
        score = self.score + self.value(move)
        # Actual move
        board = put(board, j, board[i])
        board = put(board, i, '.')

        # Special pawn stuff
        if p == 'P':
            if j - i == 2*N:
                ep = i + N
            if j - i in (N+W, N+E) and q == '.':
                board = put(board, j+S, '.')
        # We rotate the returned position, so it's ready for the next player
        return Position(board, score, wc, bc, ep, kp).rotate()

    # calcolo del valore della mossa che si intende fare sulla tabella corrente
    def value(self, move):
        # voglio andare da i a j (mossa in input)
        i, j = move
        # p pezzo in i e j pezzo in j
        p, q = self.board[i], self.board[j]
        # lo score diventa la differenza tra il pezzo nel posto vecchio ed il pezzo nel posto nuovo
        score = pst[p][j] - pst[p][i]
        # se in q(posizione in cui voglio andare) c'è un pezzo nemico lo score incrementa del suo valore che occupava
        if q.islower():
            incremento_per_cattura = pst[q.upper()][j]
            score += incremento_per_cattura

        if p == 'P':
            #se la posizione in cui voglio andare è la PROMOZIONE  ## decreto vittoria
            if A8 <= j <= H8:#j <= H8:
                # incremento lo score con quello della regina (meno quello del pedone che ho promosso) ###VITTORIA
                #score += pst['Q'][j] - pst['P'][j]
                score += 160000000

        # se vado in una posizione che rischio di essere mangiato da un altro pedone disincentivo a scegliere quella mossa
        # decrementando lo score
        if p == 'P':
            diag_sx = self.board[j-11]
            centr = self.board[j-10]
            diag_dx = self.board[j-9]
            if (diag_sx == 'p' or diag_dx == 'p' or diag_sx == 'k' or diag_dx == 'k' or centr == 'k'):
                score -= pst[p][j]/2

        return score

Entry = namedtuple('Entry', 'depth score gamma move')
tp = OrderedDict()


################################################################################
# User interface
###############################################################################

# Python 2 compatability
if sys.version_info[0] == 2:
    input = raw_input

# funzione che mi traduce una posizione da a4 a 61
def parse(c):
    fil, rank = ord(c[0]) - ord('a'), int(c[1]) - 1
    return A1 + fil - 10*rank

# funzione che mi mette la posizione da numero 61 ad a4
def render(i):
    rank, fil = divmod(i - A1, 10)
    return chr(fil + ord('a')) + str(-rank + 1)

contatorefile = 0

ui = None
TABELLA = None
Dialog = None
app = None
inexec = False
contatorefile = 0
def main():
    import sys
    global ui
    global Dialog
    global app
    global TABELLA
    global inexec
    global out_file
    pathfile = path_file_debug+("tabelleconsiderate%d.txt" % (contatorefile))
    out_file = open(pathfile,"w")
    print("inesec:", inexec)
    if app is None:
        app = QtGui.QApplication(sys.argv)
    print(app)
    Dialog = QtGui.QDialog()
    print(Dialog)
    ui = Ui_Dialog()
    ui.setupUi(Dialog, TABELLA)
    ui.bottone.clicked.connect(callbackperGUI)
    ui.comboBox.currentIndexChanged['QString'].connect(handleChanged)
    ui.comboBox.highlighted['QString'].connect(handleChanged) ##### questo sottolineato fa vedere le mosse
    TABELLA = Position(config_iniziale, 0, (True,True), (True,True), 0, 0)
    print(' '.join(TABELLA.board))
    global contatorefile
    ui.colora(TABELLA)
    posizioni = TABELLA.genMoves()
    ui.comboBox.clear()
    # stampo tutte le mie mosse possibili in questo istante da mostrare all'utente per la scelta
    for j in posizioni:
        posizione = render(j[0]) + render(j[1])
        print (posizione) #render serve per stamparmelo nel formato [a2a3]
        ui.comboBox.addItem(posizione)
    Dialog.show()
    #print("appexec:",app.exec_())
    if not inexec:
        inexec = True
        app.exec_()

#  illumina le mosse al passare del mouse sulle opzioni del menù a tendina
def handleChanged(text):
    global Dialog
    text = str(text)
    # se la stringa è alpfanumerica e di 4 lettere/numeri allora è una mossa
    if (text.isalnum() and len(text)==4):
        # riaggiorna
        ui.colora(TABELLA)
        # label attuale del pezzo
        partenza = parse(str(text[0:2]))
        stringa_partenza = "l%d" % partenza
        # label di arrivo del pezzo
        arrivo = parse(str(text[2:4]))
        stringa_arrivo = "l%d" % arrivo
        # coloro la label di arrivo
        label_da_colorare_arrivo = Dialog.findChild(QtGui.QLabel, stringa_arrivo)
        label_da_colorare_arrivo.setStyleSheet("QLabel {background-color: rgb(173, 220, 243);border: 1px solid rgb(0, 0, 0);}")
        # coloro la label di partenza
        label_da_colorare_partenza = Dialog.findChild(QtGui.QLabel, stringa_partenza)
        label_da_colorare_partenza.setStyleSheet("QLabel {background-color: rgb(173, 220, 243);border: 1px solid rgb(0, 0, 0);}")

def callbackperGUI():
    global TABELLA
    global ui
    global Dialog
    global app
    global file_mossa_migl

    print(' '.join(TABELLA.board))

    move = None

    print ("testo nella finestra %s\n" % ui.comboBox.currentText())
    # ciclo che aspetta che l'utente immetta una giusta mossa
    crdn = str(ui.comboBox.currentText()) #input("Your move: ")
    move = parse(crdn[0:2]), parse(crdn[2:4])    #parse ti mette dal formato a4 a 71
    # mossa del giocatore persona
    TABELLA = TABELLA.move(move)
    #global xxx
    #print ("valore di XXX:",xxx)
    # visualizza la mia mossa che ho appena fatto
    print(' '.join(TABELLA.rotate().board))
    ui.colora(TABELLA.rotate())
    Dialog.update()

    score = alphabetamax(TABELLA, -9999999999, +9999999999, 5, True)
    move = tentativo_mossa
    print ("score con minmax a b: %d\n" % score)
    if (tentativo_mossa is not None):
        stringa = "avrei trovato la mossa: %s - %s\n" %(render(119 - tentativo_mossa[0]), render(119 - tentativo_mossa[1]))
        print(stringa)
        file_mossa_migl.write(stringa)
    # controllo che qualcuno non abbia vinto/perso
    print("move: ", move," - score: ", score)
    # stamperai in una label il risultato, blocchi il tasto e chiedi se vuole una nuova partita e rifai il main
    if score <= -MATE_VALUE:
        TABELLA = TABELLA.move(move)
        ui.colora(TABELLA)
        popupVittoriaSconfitta("VINTO")
        #print("You won")
        #break
    elif score >= MATE_VALUE:
        TABELLA = TABELLA.move(move)
        ui.colora(TABELLA)
        popupVittoriaSconfitta("PERSO")
        #print("You lost")
        #break
    else:
        # stampa la mossa corretta del CPU nel formato esempio : a2b3
        # il 119- serve per visualizzarlo dalla parte dello sfidante
        print("My move:", render(119-move[0]) + render(119-move[1]))
        # faccio la mossa CPU
        TABELLA = TABELLA.move(move)
        ui.colora(TABELLA)
        #Dialog.show()
        posizioni = TABELLA.genMoves()
        ui.comboBox.clear()
        # stampo tutte le mie mosse possibili in questo istante da mostrare all'utente per la scelta
        for j in posizioni:
            posizione = render(j[0]) + render(j[1])
            print (posizione) #render serve per stamparmelo nel formato [a2a3]
            ui.comboBox.addItem(posizione)

# popup che compare quando si ha un risultato del math, chiede inoltre se si vuole fare un'altra partita
def popupVittoriaSconfitta(ris):
    global Dialog
    global app
    Stringa = "HAI %s ! \n VUOI GIOCARE ANCORA? \n" % ris
    reply = QtGui.QMessageBox.question(Dialog, 'Message',
            Stringa, QtGui.QMessageBox.Yes |
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)
    # se l'utente intende fare un'altra partita richiama main()
    if reply == QtGui.QMessageBox.Yes:
        main()
    else:
        exit()


# variabile globale che identifica la prossima mossa CPU
tentativo_mossa = None
def alphabetamax(t, alpha, beta, depthLeft, primo = False):
    global tentativo_mossa
    global file_aggiorno_migliore
    #if tentativo_mossa is not None:
        #print("[MAX]tentativo mossa: "+render(119-tentativo_mossa[0]) + " - " + render(119-tentativo_mossa[1]) + "\n")
    if(depthLeft == 0):
        return t.score
    mosse_poss = t.genMoves()
    for m in mosse_poss :
        stringa = render(m[0]) + " - " + render(m[1]) + "\n"
        if primo:
            print (stringa)
            file_mosse.write(stringa)
    file_mosse.write(' '.join(t.board))
    for move in sorted(t.genMoves(), key=t.value, reverse=True):
        # chiamo alphabetamin
        s = alphabetamin(t.move(move),alpha, beta, depthLeft - 1)

        if s >= beta:
            stringa = "aggiorno la mossa a: "+render(move[0]) + " - " + render(move[1]) + "\n"
            if primo:
                print ('s>=beta e primo vale:',primo)
                print (stringa)
                file_aggiorno_migliore.write(stringa)
                tentativo_mossa = move
            return beta
        # penso che sia la sorta di potatura, tutto buono se sta sopra a gamma
        if s > alpha:
            stringa = "aggiorno la mossa a: "+render(move[0]) + " - " + render(move[1]) + "\n"
            if primo:
                file_aggiorno_migliore.write(stringa)
                tentativo_mossa = move
            alpha = s
    return alpha


def alphabetamin(t, alpha, beta, depthLeft):
    # se la profondità permessa è 0 torna
    if(depthLeft == 0):
        return -t.score
    # insieme delle mosse possibili
    mosse_poss = t.genMoves()
    # per ogni mossa che genera un sucessore
    for move in sorted(t.genMoves(), key=t.value, reverse=True):
        # chiamo alphabetamax
        s = alphabetamax(t.move(move),alpha, beta, depthLeft - 1)
        # se s è minore/uguale di Alfa fai la potatura e non visitare quel sottoalbero
        if s <= alpha:
            return alpha
        # aggiornamento di Beta, se s è minore di Beta corrente
        if s < beta:
            beta = s
    return beta


if __name__ == '__main__':
    main()
