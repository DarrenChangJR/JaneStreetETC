#!/usr/bin/env python3
# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py --test prod-like; sleep 1; done

import argparse
from collections import deque
from enum import Enum
import time
import socket
import json

team_name = "NAF"

def main():
    args = parse_arguments()

    exchange = ExchangeConnection(args=args)

    hello_message = exchange.read_message()
    print("First message from exchange:", hello_message)
    ordID = 1
    
    bond_bid_price, bond_ask_price = None, None
    vale_bid_price, vale_ask_price = None, None
    valbz_bid_price, valbz_ask_price = None, None
    GS_bid_price, GS_ask_price = None, None
    MS_price, MS_ask_price = None, None
    WFC_bid_price, WFC_ask_price = None, None
    XLF_bid_price, XLF_ask_price = None, None



    xlf_last_print_time = time.time()
    last_ADR_time = time.time()

    vale_in_hand = 0


    while True:
        message = exchange.read_message()

        if message["type"] == "close":
            print("The round has ended")
            break
        elif message["type"] == "error":
            print(message)
        elif message["type"] == "reject":
            print(message)
        elif message["type"] == "fill":
            print(message)
        elif message["type"] == "book":

            if message["type"] == "XLF":
                def best_price(side):
                    if message[side]:
                        return message[side][0][0]

                XLF_bid_price = best_price("buy")
                XLF_ask_price = best_price("sell")

            if message["type"] == "GS":
                def best_price(side):
                    if message[side]:
                        return message[side][0][0]

                GS_bid_price = best_price("buy")
                GS_ask_price = best_price("sell")

            if message["type"] == "MS":
                def best_price(side):
                    if message[side]:
                        return message[side][0][0]

                MS_bid_price = best_price("buy")
                MS_ask_price = best_price("sell")

            if message["type"] == "WFC":
                def best_price(side):
                    if message[side]:
                        return message[side][0][0]

                WFC_bid_price = best_price("buy")
                WFC_ask_price = best_price("sell")

            if (XLF_bid_price != None and GS_ask_price != None and MS_ask_price != None and WFC_ask_price != None):
                bucket_ask = (3 * 1000 + 2 * GS_ask_price + 3 * MS_ask_price + 2 * WFC_ask_price)/10
                if (XLF_bid_price >  bucket_ask):
                    exchange.send_add_message(order_id=ordID, symbol="XLF", dir=Dir.SELL, price=XLF_bid_price, size=10)
                    ordID += 1
                    exchange.send_add_message(order_id=ordID, symbol="BOND", dir=Dir.BUY, price=bond_ask_price, size=3)
                    ordID += 1
                    exchange.send_add_message(order_id=ordID, symbol="GS", dir=Dir.BUY, price=GS_ask_price, size=2)
                    ordID += 1
                    exchange.send_add_message(order_id=ordID, symbol="MS", dir=Dir.BUY, price=MS_ask_price, size=3)
                    ordID += 1
                    exchange.send_add_message(order_id=ordID, symbol="WFC", dir=Dir.BUY, price=WFC_ask_price, size=2)
                    ordID += 1

            if (XLF_ask_price != None and GS_bid_price != None and MS_bid_price != None and WFC_bid_price != None):
                bucket_bid = (3 * 1000 + 2 * GS_bid_price + 3 * MS_bid_price + 2 * WFC_bid_price)/10
                if (XLF_ask_price < bucket_bid):
                    exchange.send_add_message(order_id=ordID, symbol="XLF", dir=Dir.BUY, price=XLF_ask_price, size=10)
                    ordID += 1
                    exchange.send_add_message(order_id=ordID, symbol="BOND", dir=Dir.SELL, price=bond_bid_price, size=3)
                    ordID += 1
                    exchange.send_add_message(order_id=ordID, symbol="GS", dir=Dir.SELL, price=GS_bid_price, size=2)
                    ordID += 1
                    exchange.send_add_message(order_id=ordID, symbol="MS", dir=Dir.SELL, price=MS_bid_price, size=3)
                    ordID += 1
                    exchange.send_add_message(order_id=ordID, symbol="WFC", dir=Dir.SELL, price=WFC_bid_price, size=2)
                    ordID += 1




# ~~~~~============== PROVIDED CODE ==============~~~~~

# You probably don't need to edit anything below this line, but feel free to
# ask if you have any questions about what it is doing or how it works. If you
# do need to change anything below this line, please feel free to


class Dir(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExchangeConnection:
    def __init__(self, args):
        self.message_timestamps = deque(maxlen=500)
        self.exchange_hostname = args.exchange_hostname
        self.port = args.port
        exchange_socket = self._connect(add_socket_timeout=args.add_socket_timeout)
        self.reader = exchange_socket.makefile("r", 1)
        self.writer = exchange_socket

        self._write_message({"type": "hello", "team": team_name.upper()})

    def read_message(self):
        """Read a single message from the exchange"""
        message = json.loads(self.reader.readline())
        if "dir" in message:
            message["dir"] = Dir(message["dir"])
        return message

    def send_add_message(
        self, order_id: int, symbol: str, dir: Dir, price: int, size: int
    ):
        """Add a new order"""
        self._write_message(
            {
                "type": "add",
                "order_id": order_id,
                "symbol": symbol,
                "dir": dir,
                "price": price,
                "size": size,
            }
        )

    def send_convert_message(self, order_id: int, symbol: str, dir: Dir, size: int):
        """Convert between related symbols"""
        self._write_message(
            {
                "type": "convert",
                "order_id": order_id,
                "symbol": symbol,
                "dir": dir,
                "size": size,
            }
        )

    def send_cancel_message(self, order_id: int):
        """Cancel an existing order"""
        self._write_message({"type": "cancel", "order_id": order_id})

    def _connect(self, add_socket_timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if add_socket_timeout:
            # Automatically raise an exception if no data has been recieved for
            # multiple seconds. This should not be enabled on an "empty" test
            # exchange.
            s.settimeout(5)
        s.connect((self.exchange_hostname, self.port))
        return s

    def _write_message(self, message):
        what_to_write = json.dumps(message)
        if not what_to_write.endswith("\n"):
            what_to_write = what_to_write + "\n"

        length_to_send = len(what_to_write)
        total_sent = 0
        while total_sent < length_to_send:
            sent_this_time = self.writer.send(
                what_to_write[total_sent:].encode("utf-8")
            )
            if sent_this_time == 0:
                raise Exception("Unable to send data to exchange")
            total_sent += sent_this_time

        now = time.time()
        self.message_timestamps.append(now)
        if len(
            self.message_timestamps
        ) == self.message_timestamps.maxlen and self.message_timestamps[0] > (now - 1):
            print(
                "WARNING: You are sending messages too frequently. The exchange will start ignoring your messages. Make sure you are not sending a message in response to every exchange message."
            )


def parse_arguments():
    test_exchange_port_offsets = {"prod-like": 0, "slower": 1, "empty": 2}

    parser = argparse.ArgumentParser(description="Trade on an ETC exchange!")
    exchange_address_group = parser.add_mutually_exclusive_group(required=True)
    exchange_address_group.add_argument(
        "--production", action="store_true", help="Connect to the production exchange."
    )
    exchange_address_group.add_argument(
        "--test",
        type=str,
        choices=test_exchange_port_offsets.keys(),
        help="Connect to a test exchange.",
    )

    # Connect to a specific host. This is only intended to be used for debugging.
    exchange_address_group.add_argument(
        "--specific-address", type=str, metavar="HOST:PORT", help=argparse.SUPPRESS
    )

    args = parser.parse_args()
    args.add_socket_timeout = True

    if args.production:
        args.exchange_hostname = "production"
        args.port = 25000
    elif args.test:
        args.exchange_hostname = "test-exch-" + team_name
        args.port = 25000 + test_exchange_port_offsets[args.test]
        if args.test == "empty":
            args.add_socket_timeout = False
    elif args.specific_address:
        args.exchange_hostname, port = args.specific_address.split(":")
        args.port = int(port)

    return args


if __name__ == "__main__":
    # Check that [team_name] has been updated.
    assert (
        team_name != "REPLACEME"
    ), "Please put your team name in the variable [team_name]."

    main()

