#!/usr/bin/env pypy
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
from itertools import count
from collections import namedtuple
from graficaS import *

# variabili globali di servizio
ui = None
ChessBoard = None
Dialog = None
app = None
inexec = False
# variabile globale che identifica la prossima mossa CPU
move_cpu = None
# costanti di profondità e infinito
depth = 5
INF = 9999999999
# posizioni border della mia scacchiera in coordinate = interi
A1, H1, A8, H8 = 91, 98, 21, 28
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


# dict PLAYER e CPU per valutazione di Pedoni e la loro altezza nel gioco
dictP = {20 : 100, 30 : 70, 40 : 60, 50 : 40, 60 : 20, 70 : 10, 80 : 0}
dictp = {90 : 100, 80 : 70, 70 : 60, 60 : 40, 50 : 20, 40 : 10, 30 : 0}

# tabella delle direzioni che pedone e re possono assumere
N, E, S, W = -10, 1, 10, -1
directions = {
    'P': (N, 2*N, N+W, N+E),
    'K': (N, E, S, W, N+E, S+E, S+W, N+W)
}

class Position(namedtuple('Position', 'board ep')):

    #genera tutte le mosse che un giocatore puo effettuare di tutti i pezzi di un giocatore
    def genMoves(self):
        # controllo se sono sotto scacco..
        scacco = self.kept_in_check()
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
                    # Gestione del movimento dei pedoni in diagonale e controllo per en passant
                    # (muovi in diag solo se mangi qualcuno o en passant)
                    if p == 'P' and d in (N+W, N+E) and q == '.' and j != self.ep : break
                    # senza enpassant
                    # if p == 'P' and d in (N+W, N+E) and q == '.' : break
                    # Gestione del movimento dei pedoni in verticale di 1 o 2 caselle
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
                    # Non continuare
                    if p in ('P', 'K'): break
                    # Non continuare oltre perche c'è un altro pezzo
                    if q.islower(): break

    # funzione che determina se la tabella è in una condizione di scacco
    def kept_in_check(self):
    # controllo che non si sia in una situazione di scacco
        for i, p in enumerate(self.board):
            # sono sotto scacco se un pedone è nella cella diagonale(sx o dx) al re, è l'unico modo per avere uno scacco se si
            # hanno solo pedoni
            if (p == 'K') and (self.board[i-11] == 'p' or self.board[i-9] == 'p'):
                return True
        return False

    # rotazione della scacchiera
    # [::-1] capovolge la lista di caratteri/scacchiera
    def rotate(self):
        return Position(
            self.board[::-1].swapcase(), 119 - self.ep)

    # effettua la mossa, aggiorna score e torna la nuova tabella aggiornata
    def move(self, move):
        # i casella iniziale della mossa move, j casella in cui ci si intende muovere
        i, j = move
        # pezzo corrente(p) e pezzo che c'è nella futura locazione(q)
        p, q = self.board[i], self.board[j]
        # funzione anonima che mette il pezzo p nel posto i
        put = lambda board, i, p: board[:i] + p + board[i+1:]
        board = self.board
        # riaggiorno en passant a zero
        ep = 0
        # Compi la mossa, nel posto j metti ciò che era in posto i ed in posto i metti '.'
        board = put(board, j, board[i])
        board = put(board, i, '.')

        # EN PASSANT, se mossa è in diagonale e in q c'è '.' allora in j+S metti '.'
        # al posto di 'p'
        if p == 'P':
            if j - i in (N+W, N+E) and q == '.':    # se il diagonale non è un pedone da mangiare sei in enpassant...
                board = put(board, j+S, '.')        # metti nella casella in verticale di uno . perchè è li dove sta il pezzo da catturare
            if j - i == 2*N :                       # se la mossa è avanti di 2...
                ep = i + N                          # possibile enpassant in i+N
        # rotazione per prossimo giocatore
        return Position(board, ep).rotate()

# funzione che mi traduce una posizione da a1 a 21
def parse(c):
    fil, rank = ord(c[0]) - ord('a'), int(c[1]) - 1
    return A1 + fil - 10*rank

# funzione che mi mette la posizione da numero 21 ad a1
def render(i):
    rank, fil = divmod(i - A1, 10)
    return chr(fil + ord('a')) + str(-rank + 1)

def main():
    # variabili globali per GUI
    global ui, Dialog, app, ChessBoard, inexec

    if app is None:
        app = QtGui.QApplication(sys.argv)
    Dialog = QtGui.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog, ChessBoard)
    ui.bottone.clicked.connect(callbackperGUI)
    ui.comboBox.currentIndexChanged['QString'].connect(handleChanged)
    ui.comboBox.highlighted['QString'].connect(handleChanged)
    ChessBoard = Position(config_iniziale, 0)
    #print(' '.join(ChessBoard.board))
    ui.colora(ChessBoard)
    ui.comboBox.clear()

    # stampo tutte le mie mosse possibili in questo istante da mostrare all'utente per la scelta
    for j in ChessBoard.genMoves():
        posizione = render(j[0]) + render(j[1])
        #print (posizione)
        ui.comboBox.addItem(posizione)
    Dialog.show()
    # se non ho già l'app che gira eseguila
    if not inexec:
        inexec = True
        app.exec_()

#  Illumina le mosse al passare del mouse sulle opzioni del menù a tendina
def handleChanged(text):
    global Dialog
    text = str(text)
    # se la stringa è alpfanumerica e di 4 lettere/numeri allora è una mossa
    if (text.isalnum() and len(text)==4):
        # riaggiorna
        ui.colora(ChessBoard)
        # coloro la label di partenza
        label_A = Dialog.findChild(QtGui.QLabel, "l%d" % parse(str(text[0:2])))
        label_A.setStyleSheet("QLabel {background-color: rgb(173, 220, 243);border: 1px solid rgb(0, 0, 0);}")
        # coloro la label di arrivo
        label_B = Dialog.findChild(QtGui.QLabel, "l%d" % parse(str(text[2:4])))
        label_B.setStyleSheet("QLabel {background-color: rgb(173, 220, 243);border: 1px solid rgb(0, 0, 0);}")

# Alla pressione del tasto Move viene richiamata questa procedura
def callbackperGUI():
    # var globali per GUI
    global ChessBoard, ui
    # mossa da fare nella scacchiera
    move = None
    # prelevo la mossa dalla combo box
    textCB = str(ui.comboBox.currentText())
    move = parse(textCB[0:2]), parse(textCB[2:4])
    # muovi la scacchiera in seguito alla mossa decisa da PLAYER
    ChessBoard = ChessBoard.move(move)
    # ridiisegna la scacchiera nuova
    ui.colora(ChessBoard.rotate())

    score = alphabetamax(ChessBoard, -INF, +INF, depth, True)
    # mossa pensata dalla CPU
    move = move_cpu
    # calcolo la nuova scacchiera in seguito alla mossa CPU
    ChessBoard = ChessBoard.move(move)
    # aggiorno le statistiche dei due giocatori (numero di pedoni)
    pawns_player, pawns_cpu = getStatistics(ChessBoard)
    ui.label_20.setText("%d pawns" % pawns_player)
    ui.label_21.setText("%d pawns" % pawns_cpu)

    # controllo che la partita non sia terminata con SCONFITTA o VITTORIA
    if testTerminazione(ChessBoard) and score < 0:
        ui.colora(ChessBoard)
        popupVittoriaSconfitta("WIN")

    elif testTerminazione(ChessBoard) and score > 0:
        ui.colora(ChessBoard)
        popupVittoriaSconfitta("LOSE")
    # vado avanti nella partita
    else:
        ui.colora(ChessBoard)
        posizioni = ChessBoard.genMoves()
        ui.comboBox.clear()
        # se non ho mosse possibili dichiari persa con SCACCO MATTO
        if (len(list(posizioni)) == 0):
            popupVittoriaSconfitta("LOSE - CHECKMATE")
        # mostro all'utente nella ComboBox tutte le mosse che può effettuare
        for j in ChessBoard.genMoves():
            posizione = render(j[0]) + render(j[1])
            ui.comboBox.addItem(posizione)

# popup che compare quando si ha un risultato del math, chiede inoltre se si vuole fare un'altra partita
def popupVittoriaSconfitta(ris):
    global Dialog
    # stringa di richiesta gioco
    Stringa = "YOU %s ! \n DO YOU WANT RESTART THE GAME? \n" % ris
    reply = QtGui.QMessageBox.question(Dialog, 'GAME OVER',
            Stringa, QtGui.QMessageBox.Yes |
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)
    # se l'utente intende fare un'altra partita richiama main()
    if reply == QtGui.QMessageBox.Yes:
        main()
    else:
        exit()

# funzione che torna il conto dei pedoni del PLAYER e del CPU e le ritorna in una coppia
def getStatistics(t):
    pawns_player = 0
    pawns_cpu = 0
    for j in range(21, 99):
        p = t.board[j]
        if p == 'P':
            pawns_player += 1
        if p == 'p':
            pawns_cpu += 1
    return (pawns_player, pawns_cpu)


##############################################################################################
#                                                                                            #
#    ALGORITMO MINMAX CON POTATURA ALPHABETA, FUNZIONE DI VALUTAZIONE E TEST TERMINAZIONE    #
#                                                                                            #
##############################################################################################

# GIOCATORE MAX DELL'ALGORITMO MINMAX CON POTATURA ALPHA-BETA
def alphabetamax(t, alpha, beta, d, recordmove = False):
    global move_cpu

    if testTerminazione(t) or (d == 0):
        return h(t)

    s = -INF
    for move in sorted(t.genMoves()):
        # chiamo alphabetamin
        s = max(s, alphabetamin(t.move(move),alpha, beta, d - 1))

        if s >= beta: return s
        # penso che sia la sorta di potatura, tutto buono se sta sopra a gamma
        if s > alpha:
            if recordmove:
                move_cpu = move
            alpha = s
    return s

# GIOCATORE MIN DELL'ALGORITMO MINMAX CON POTATURA ALPHA-BETA
def alphabetamin(t, alpha, beta, d):

    if testTerminazione(t) or (d == 0):
        #print ("chiamo -h(t) per test Terminazione\n")
        return -h(t)

    s = +INF
    # per ogni mossa che genera un sucessore
    for move in sorted(t.genMoves()):
        # chiamo alphabetamax
        s = min(s, alphabetamax(t.move(move),alpha, beta, d - 1))
        # se s è minore/uguale di Alfa fai la potatura e non visitare quel sottoalbero
        if s <= alpha: return s
        # aggiornamento di Beta, se s è minore di Beta corrente
        beta = min(beta, s)
    return s

# FUNZIONE DI VALUTAZIONE DELLA ChessBoard CORRENTE
def h(tab):
    # inizializzazione dello score a zero
    score = 0
    # per ogni posizione della scacchiera
    for j in range(21, 99):
        # prelevo il pezzo alla posizione j che sto considerando
        p = tab.board[j]
        if p == 'P':
            # incremento per pedone ancora in gioco +10
            score += 10
            # incremento dello score per l'altezza del pedone che sto considerando
            score += dictP[j - (j%10)]
            # decremento se metto un pedone in difficoltà
            diag_sx = tab.board[j-11]
            centr = tab.board[j-10]
            diag_dx = tab.board[j-9]
            if (diag_sx == 'p' or diag_dx == 'p' or diag_sx == 'k' or diag_dx == 'k' or centr == 'k'):
                score = score / 1.5
            # impenno il valore al positivo per vittoria
            if j in range (21, 29):
                score = +99999

        # guardo i pedoni avversari come sono posizionati
        if p == 'p':
            # decremento per pedone ancora in gioco dell'avversario
            score -= 10
            # decremento dello score per l'altezza del pedone avversario che sto considerando
            score -= dictp[j - (j%10)]
            # incremento lo score se ho la possibilità di mangiare un pedone
            diag_sx = tab.board[j+11]
            centr = tab.board[j+10]
            diag_dx = tab.board[j+9]
            if (diag_sx == 'P' or diag_dx == 'P' or diag_sx == 'K' or diag_dx == 'K' or centr == 'K'):
                score = score*1.5
            # impenno il valore al negativo per sconfitta
            if j in range (91, 99):
                score = -99999

    return score

# TEST DI TERMINAZIONE PER UNA ChessBoard DATA IN INPUT
def testTerminazione(t):
    # se nelle righe di fondo scacchiera c'è un pedone avversario torno True, False altrimenti
    for i in range(21, 29):
        #if t.board[i] != '.' and t.board[i] != 'k' and t.board[i] != 'K' and t.board[i] != 'p':
        if t.board[i] == 'P':
            return True
    for i in range(91, 99):
        #if t.board[i] != '.' and t.board[i] != 'k' and t.board[i] != 'K' and t.board[i] != 'P':
        if t.board[i] == 'p':
            return True
    return False

# MAIN()
if __name__ == '__main__':
    main()


