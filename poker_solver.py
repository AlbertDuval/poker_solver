#! /usr/bin/python

import sys
import time
import math

from enum import Enum
from copy import deepcopy
from typing import Tuple
from itertools import combinations, combinations_with_replacement

from multiprocessing import Lock, Process, Queue, current_process, cpu_count
# print("Number of cpu : ", cpu_count())
import queue # imported for using queue.Empty exception

# import platform
# print(platform.python_version())

from pydealer import Deck
from pydealer.card import Card
from pydealer.const import (
    DEFAULT_RANKS,
    POKER_RANKS,
    VALUES,
    SUITS)


class Value(Enum):
    T = 10
    J = 11
    Q = 12
    K = 13
    A = 14


class Color(Enum):
    H = 1
    D = 2
    C = 3
    S = 4


COLOR = {
    "Spades": "\x06",
    "Hearts": "\x03",
    "Clubs": "\x05",
    "Diamonds": "\x04"
}

ROLOC = {
    "S": "Spades",
    "H": "Hearts",
    "C": "Clubs",
    "D": "Diamonds",
}

VALEUR = {
    "Ace": "A",
    "King": "K",
    "Queen": "Q",
    "Jack": "J",
    "10": "T",
    "9": "9",
    "8": "8",
    "7": "7",
    "6": "6",
    "5": "5",
    "4": "4",
    "3": "3",
    "2": "2",
}

RUELAV = {v: k for k, v in VALEUR.items()}


# Preset defintion of weighted theorical ordered hands for 1, 2, 3 and 5 size cases
HAUTEUR1 = [c for c in combinations(range(13, 0, -1), 1)][::-1]
HAUTEUR2 = [c for c in combinations(range(13, 0, -1), 2)][::-1]
HAUTEUR3 = [c for c in combinations(range(13, 0, -1), 3)][::-1]
HAUTEUR5 = [c for c in combinations(range(13, 0, -1), 5)][::-1]

# print(*map(str, map(len, [HAUTEUR1, HAUTEUR2, HAUTEUR3, HAUTEUR5])))
# print("HAUTEUR1=", HAUTEUR1)
# print("HAUTEUR2=", HAUTEUR2)
# print("HAUTEUR3=", HAUTEUR3)
# print("HAUTEUR5=", HAUTEUR5)


class MyCard(Card):
    """
    MyCard inherit from Card with representation overload
    """
    def __init__(self, *args):
        if len(args) == 2:
            value, suit = args[0], args[1]
        elif len(args) == 1:
            arg = args[0]
            if len(arg) != 2:
                raise ValueError("Invalid parameters for MyCard")
            value = RUELAV[arg[0]]
            suit = ROLOC[arg[1]]
        else:
            raise AttributeError("Invalid parameters for MyCard")
        super().__init__(value, suit)

    def __str__(self):
        """
        Overload of __str__ for better understanding
        """
        return("{}{}".format(VALEUR[self.value], COLOR[self.suit]))


class ProgressBar:
    def __init__(self, width, sleep=0):
        self.progress = 0
        self.toolbar_width = 50
        self.width = width
        self.sleep = sleep

        sys.stdout.write("[%s] (0/%i)" % (" " * self.toolbar_width, self.width))
        sys.stdout.flush()
        sys.stdout.write("\b" * (self.toolbar_width+20)) # return to start of line, after '['

        # print("[%s] (0/%i)" % (" " * toolbar_width, toolbar_width), flush=True)
        # sys.stdout.write("\b" * (toolbar_width*2)) # return to start of line, after '['
        # print("\b" * (self.width+20), flush=True)

    def update(self):
        if self.progress < self.width:
            self.progress += 1
        self.toolbar_progress = self.progress * self.toolbar_width // self.width
        time.sleep(self.sleep)

        sys.stdout.write("[%s] (%i/%i)" % ("#" * self.toolbar_progress + " " * (self.toolbar_width - self.toolbar_progress), self.progress, self.width))
        sys.stdout.flush()
        sys.stdout.write("\b" * (self.toolbar_width+20))

        # print("[%s] (%i/%i)" % ("#" * self.progress + " " * (self.width - self.progress), self.progress, self.width), flush=True)
        # sys.stdout.write("\r" * 2)
        # print("\b" * (self.width+20), flush=True)


class CustomWorker():
    def __init__(self, main_hand, face_hand, partial_flop):
        self.main_hand = main_hand
        self.face_hand = face_hand
        self.partial_flop = partial_flop

        self.main_count = 0
        self.face_count = 0
        self.null_count = 0

    def run(self, tasks_to_accomplish, tasks_that_are_done=None):
        while True:
            try:
                '''
                    try to get task from the queue. get_nowait() function will 
                    raise queue.Empty exception if the queue is empty. 
                    queue(False) function would do the same task also.
                '''
                flop = tasks_to_accomplish.get_nowait()
            except queue.Empty:
                break
            else:
                full_flop = flop + self.partial_flop
                main_full_flop = full_flop + self.main_hand
                face_full_flop = full_flop + self.face_hand
                main_value = max(map(weigh_hand, combinations(main_full_flop, 5)))
                face_value = max(map(weigh_hand, combinations(face_full_flop, 5)))
                if main_value > face_value:
                    self.main_count += 1
                elif main_value < face_value:
                    self.face_count += 1
                else:
                    self.null_count += 1
                # print(main_value, face_value, self.main_count, self.face_count, self.null_count)
                # tasks_that_are_done.put((self.main_count, self.face_count, self.null_count))
        return True


def weigh_hand(cards: Tuple[MyCard, MyCard, MyCard, MyCard, MyCard]) -> int:
    values_cards = sorted([POKER_RANKS["values"][card.value] for card in cards], reverse=True)
    values_count = [values_cards.count(value) for value in values_cards]

    is_flush = len(set(card.suit for card in cards)) == 1
    is_quinte = len(values_cards) == 5 and len(values_cards) == len(set(values_cards)) \
        and ((values_cards[0] - values_cards[-1] == 4) or (values_cards[0] == 13 and values_cards[1] == 4))

    # print(" ".join(map(str, cards)), values_cards, values_count, is_flush)
    # value = max(values_cards)

    hauteur_cards = sorted([v for v, c in zip(values_cards, values_count) if c == 1], reverse=True)
    value = 0
    # 0 Hauteur
    if values_count.count(1) == 5:
        value = HAUTEUR5.index(tuple(hauteur_cards))
    # 1 Pair
    if values_count.count(2) == 2 and values_count.count(1) == 3:
        value = 1500 + values_cards[values_count.index(2)] * 300 + HAUTEUR3.index(tuple(hauteur_cards))
        # print(" ".join(map(str, cards)), value, values_cards[values_count.index(2)], HAUTEUR3.index(tuple(hauteur_cards)), hauteur_cards)
    # 2 Pairs
    if values_count.count(2) == 4:
        min_pair, max_pair = list(sorted(set([v for v, c in zip(values_cards, values_count) if c == 2])))
        # value = 6000 + values_cards[values_count.index(2)] * 15 + HAUTEUR1.index(tuple(hauteur_cards))
        value = 6000 + HAUTEUR2.index(tuple([max_pair, min_pair])) * 15 + HAUTEUR1.index(tuple(hauteur_cards))
        # print("doublePairs", min_pair, max_pair, hauteur_cards, HAUTEUR1.index(tuple(hauteur_cards)), value)
        # value = 6000 + max_pair * 2000 + min_pair * 100 + HAUTEUR1.index(tuple(hauteur_cards))
    # Brelan
    if values_count.count(3) == 3 and values_count.count(2) == 0:
        # value = 7000 + values_cards[values_count.index(3)] * 80 + HAUTEUR2.index(tuple(hauteur_cards))
        value = 7500 + values_cards[values_count.index(3)] * 80 + HAUTEUR2.index(tuple(hauteur_cards))
    # Quinte
    if is_quinte:
        # input("{} {}".format(value, " ".join(map(str, cards))))
        # value = 8000 + min(values_cards)
        # offset = int(values_cards[0] == 13 and values_cards[1] == 4) or min(values_cards)
        value = 9000 + min(values_cards)
        if min(values_cards) == 1 and max(values_cards) == 13: # Quinte case starting with an Ace
            value = value - 1
    # Flush
    if is_flush:
        # print("cards=", " ".join(map(str, cards)), "type_cards=", " ".join(map(str, map(type, cards))), values_cards, values_count)
        # value = 9500 + value_add
        # value = 8500 + HAUTEUR5.index(tuple(hauteur_cards))
        value = 9500 + HAUTEUR5.index(tuple(hauteur_cards))
    # Full
    if values_count.count(3) == 3 and values_count.count(2) == 2:
        value = 10000 + values_cards[values_count.index(3)] * 15 + values_cards[values_count.index(2)]
    # Carré
    if 4 in values_count:
        value = 11000 + values_cards[values_count.index(4)] * 15 + HAUTEUR1.index(tuple(hauteur_cards))
    if is_flush and is_quinte:
        value = 12000 + min(values_cards)
        if min(values_cards) == 1 and max(values_cards) == 13: # Quinte case starting with an Ace
            value = value - 1
    # print(" ".join(map(str, cards)), values_cards, values_count, "value=", value)
    return value

def poker_solve() -> None:
    cards = [MyCard(value, suit) for value in VALUES for suit in SUITS]
    # deck = Deck(cards=[MyCard(value, suit) for value in VALUES for suit in SUITS])
    deck = Deck(cards=cards, build=False)
    deck.shuffle() 

    main_hand = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["AC", "QH"]))
    partial_flop = ()
    partial_flop = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KH"]))
    # partial_flop = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KH", "KD", "6S"]))

    # _ = deck.get(MyCard("KD").name)
    # _ = deck.get(MyCard("3S").name)
    
    face_cards = [tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["TC", "TH"]))]
    # face_cards = [combinations(deck, 2)]
    droped_card = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["8H", "5S", "6C", "4H", "6H", "5C", "JH", "2S"]))
    
    print(len(cards), len(deck))

    # c1 = list(combinations(deck, 2))
    # print(c1[0], c1[1], c1[2])
    # print(len(c1))
    for face_card in face_cards:
        tmp_deck = deepcopy(deck)
        # input()
        main_count, face_count, null_count = 0, 0, 0
        len_combi = math.comb(len(tmp_deck), 5 - len(partial_flop))

        print("{} {}  VS  {} {}   ({}, {})".format(
            main_hand[0], main_hand[1],
            face_card[0], face_card[1],
            len(tmp_deck), len_combi))

        progress_bar = ProgressBar(len_combi)
        main_count, face_count, null_count = 0, 0, 0
        t0 = time.time()
        t0b = time.process_time()
        for i, flop in enumerate(combinations(tmp_deck, 5 - len(partial_flop))):
            full_flop = flop + partial_flop
            main_full_flop = full_flop + main_hand
            face_full_flop = full_flop + face_card

            main_value = max(map(weigh_hand, combinations(main_full_flop, 5)))
            face_value = max(map(weigh_hand, combinations(face_full_flop, 5)))

            if main_value > face_value:
                main_count += 1
            elif main_value < face_value:
                face_count += 1
            else:
                null_count += 1
                # print(" ".join(map(str, full_flop)))
                # print(main_value, face_value)
                # input()
            progress_bar.update()

            # if not i%200000 and i:
            if not i%100000 and i:
            # if True:
                print()
                print("{}) {} {} {} {:.2f}     {:.2f}% {:.2f}% {:.2f}%".format(
                    i,
                    main_count,
                    face_count,
                    len_combi - main_count - face_count,
                    main_count / (main_count + face_count) * 100,
                    main_count / len_combi * 100,
                    face_count / len_combi * 100,
                    null_count / len_combi * 100))
                # input()
                # pass
        print()
        print("{} {} {} {:.2f}     {:.2f}% {:.2f}% {:.2f}%".format(
            main_count,
            face_count,
            len_combi - main_count - face_count,
            main_count / (main_count + face_count) * 100,
            main_count / len_combi * 100,
            face_count / len_combi * 100,
            null_count / len_combi * 100))
        print("TIME=", time.time() - t0, time.process_time() - t0b)
        # input()

def poker_solve_multi():
    number_of_processes = 4

    number_of_task = 4
    tasks_to_accomplish = Queue()
    tasks_that_are_done = Queue()
    processes = []

    t0, t0b = time.time(), time.process_time()
    # cards =[MyCard(value, suit) for value in VALUES for suit in SUITS]
    deck = Deck(cards=[MyCard(value, suit) for value in VALUES for suit in SUITS], build=False)
    deck.shuffle()
    # main_hand = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["AS", "6H"]))
    # main_hand = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["TD", "TS"]))
    # main_hand = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["AC", "KD"]))
    # main_hand = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["AH", "3D"]))
    main_hand = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["AC", "QH"]))
    partial_flop = ()
    partial_flop = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KH"]))
    # partial_flop = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KH", "KD"]))
    # partial_flop = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KD", "TC", "JS", "TD"]))
    # partial_flop = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["7C", "2D", "7S", "4C"]))
    # partial_flop = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["9C", "6D", "JC", "7C", "2S"]))
    face_card = ()
    # face_card = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["7C", "8C"]))
    # face_card = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KS", "7S"]))
    # face_card = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KC", "KH"]))
    # face_card = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KC", "JC"]))
    face_card = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["TC", "TH"]))
    # worker = CustomWorker(main_hand, face_card, partial_flop)
    # worker = CustomWorker(main_hand, hand_cards[0], partial_flop)
    # droped_card = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["KH", "4C", "5D", "2C", "TC", "2D", "QH", "8C"]))
    droped_card = tuple(map(lambda c: deck.get(MyCard(c).name)[0], ["8H", "5S", "6C", "4H", "6H", "5C", "JH", "2S"]))

    # _ = deck.get(MyCard("9H").name)
    # _ = deck.get(MyCard("5H").name)
    # _ = deck.get(MyCard("QH").name)
    # _ = deck.get(MyCard("6D").name)

    len_combi = math.comb(len(deck), 5 - len(partial_flop))
    len_faces = math.comb(len(deck) - 5 + len(partial_flop), 2)

    if face_card:
        print("{} {}  VS  {} {},  Flop= {}   ({}, {})".format(
            main_hand[0], main_hand[1],
            face_card[0], face_card[1],
            " ".join(map(str, partial_flop)),
            len(deck), len_combi))
    else:
        print("{} {}  VS  None,  Flop= {}   ({}, {}, {})".format(
            main_hand[0], main_hand[1],
            " ".join(map(str, partial_flop)),
            len(deck), len_combi, len_faces))
        len_combi *= len_faces
    # for _, flop in enumerate(combinations(deck, 5 - len(partial_flop))):
        # tasks_to_accomplish.put(flop)
        # tasks_to_accomplish.put((main_hand, face_card, partial_flop, flop))

    for i in range(number_of_task):
        tmp_deck = deepcopy(deck)
        tasks_to_accomplish.put((i, number_of_task, main_hand, face_card, partial_flop, tmp_deck))

    # creating processes
    for _ in range(number_of_processes):
        # p = Process(target=worker.run, args=(tasks_to_accomplish, ))
        # p = Process(target=worker.run, args=(tasks_to_accomplish, tasks_that_are_done))
        # p = Process(target=do_job, args=(tasks_to_accomplish, tasks_that_are_done))
        p = Process(target=poker_solve_submission, args=(tasks_to_accomplish, tasks_that_are_done))
        processes.append(p)
        p.start()

    # completing process
    for p in processes:
        p.join()

    # print the output
    print()
    main_count, face_count, null_count = 0, 0, 0
    while not tasks_that_are_done.empty():
        m, f, n = tasks_that_are_done.get()
        print((m, f, n, sum([m, f, n]), len_combi))
        main_count += m
        face_count += f
        null_count += n
        
    print("{} {} {} {:.2f}     {:.2f}% {:.2f}% {:.2f}%".format(
        main_count,
        face_count,
        len_combi - main_count - face_count,
        main_count / (main_count + face_count) * 100,
        main_count / len_combi * 100,
        face_count / len_combi * 100,
        null_count / len_combi * 100))
    print("TIME=", time.time() - t0, time.process_time() - t0b)
    # print("{} {} {} {:.2f}     {:.2f}% {:.2f}% {:.2f}%".format(
    #     worker.main_count,
    #     worker.face_count,
    #     len_combi - worker.main_count - worker.face_count,
    #     worker.main_count / (worker.main_count + worker.face_count) * 100,
    #     worker.main_count / len_combi * 100,
    #     worker.face_count / len_combi * 100,
    #     worker.null_count / len_combi * 100))

def poker_solve_submission(tasks_to_accomplish, tasks_that_are_done=None):
    main_count, face_count, null_count = 0, 0, 0
    while True:
        try:
            '''
                try to get task from the queue. get_nowait() function will 
                raise queue.Empty exception if the queue is empty. 
                queue(False) function would do the same task also.
            '''
            task = tasks_to_accomplish.get_nowait()
        except queue.Empty:
            break
        else:
            task_num, num_proc, main_hand, face_hand, partial_flop, deck = task
            # print(len(deck), current_process().name)
            if not task_num:
                # len_combi = math.comb(len(deck), 5 - len(partial_flop))
                # progress_bar = ProgressBar(len_combi)
                pass
            count_iteration = 0
            for i, flop in enumerate(combinations(deck, 5 - len(partial_flop))):
                if not task_num:
                    # progress_bar.update()
                    pass
                if i%num_proc != task_num:
                    continue
                full_flop = flop + partial_flop
                main_full_flop = full_flop + main_hand
                main_value = max(map(weigh_hand, combinations(main_full_flop, 5)))
                if face_hand:
                    face_full_flop = full_flop + face_hand
                    face_value = max(map(weigh_hand, combinations(face_full_flop, 5)))
                    # print(main_value, face_value, current_process().name)
                    # print(task, current_process().name)
                    if main_value > face_value:
                        main_count += 1
                        # if main_value > 0 and main_value < 9000:
                        # #     if MyCard("AH") in full_flop:
                        #     count_iteration += 1
                        #     print("[{}] flop= {}, {} ({}), {} ({})".format(
                        #         count_iteration,
                        #         " ".join(map(str, full_flop)),
                        #         " ".join(map(str, main_hand)), main_value,
                        #         " ".join(map(str, face_hand)), face_value))
                        #     print("main_count= {}, face_count= {}, null_count= {}".format(
                        #         main_count, face_count, null_count))
                    elif main_value < face_value:
                        face_count += 1
                        # if MyCard("AD") in full_flop:
                        # count_iteration += 1
                        # print("[{}] flop= {}, {} ({}), {} ({})".format(
                        #     count_iteration,
                        #     " ".join(map(str, full_flop)),
                        #     " ".join(map(str, main_hand)), main_value,
                        #     " ".join(map(str, face_hand)), face_value))
                        # print("main_count= {}, face_count= {}, null_count= {}".format(
                        #     main_count, face_count, null_count))
                    else:
                        null_count += 1
                        count_iteration += 1
                        # print("[{}] flop= {}, {} ({}), {} ({})".format(
                        #     count_iteration,
                        #     " ".join(map(str, full_flop)),
                        #     " ".join(map(str, main_hand)), main_value,
                        #     " ".join(map(str, face_hand)), face_value))
                        # print("main_count= {}, face_count= {}, null_count= {}".format(
                        #     main_count, face_count, null_count))
                    # count_iteration += 1
                    # print("[{}] flop= {}, {} ({}), {} ({})".format(
                    #     count_iteration,
                    #     " ".join(map(str, full_flop)),
                    #     " ".join(map(str, main_hand)), main_value,
                    #     " ".join(map(str, face_hand)), face_value))
                    # print("main_count= {}, face_count= {}, null_count= {}".format(
                    #     main_count, face_count, null_count))
                else:
                    tmp_deck = deepcopy(deck)
                    for flop_card in flop:
                        tmp_deck.get(flop_card.name)
                    # len_face = math.comb(len(tmp_deck), 2))
                    # print(len(deck), len(tmp_deck), len(flop), len_face, current_process().name)
                    for tmp_face_hand in combinations(tmp_deck, 2):
                    # for _, tmp_face_hand in enumerate(combinations(tmp_deck, 2)):
                        face_full_flop = full_flop + tmp_face_hand
                        face_value = max(map(weigh_hand, combinations(face_full_flop, 5)))
                        # print(main_value, face_value, current_process().name)
                        # print(task, current_process().name)
                        if main_value > face_value:
                            main_count += 1
                        elif main_value < face_value:
                            face_count += 1
                        else:
                            null_count += 1

    tasks_that_are_done.put((main_count, face_count, null_count))
    return True


if __name__ == '__main__':
    poker_solve()
    poker_solve_multi()
