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

    vale_bid_price, vale_ask_price = None, None
    valbz_bid_price, valbz_ask_price = None, None
    


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
            
            if message["symbol"] == "VALE":

                def best_price(side):
                    if message[side]:
                        return message[side][0][0]

                vale_bid_price = best_price("buy")
                vale_ask_price = best_price("sell")


            if message["symbol"] == "VALBZ":

                def best_price(side):
                    if message[side]:
                        return message[side][0][0]

                valbz_bid_price = best_price("buy")
                valbz_ask_price = best_price("sell")

                now = time.time()

                # ADR Arbitrage
                if now > last_ADR_time + 1:
                    last_ADR_time = now

                    # if (bond_ask_price < 1000):
                    exchange.send_add_message(order_id=ordID, symbol="BOND", dir=Dir.BUY, price=999, size=100)
                    ordID += 1

                    # if (bond_bid_price < 1000):
                    exchange.send_add_message(order_id=ordID, symbol="BOND", dir=Dir.SELL, price=1001, size=100)
                    ordID += 1

                    trade_size = 1

                    if (vale_ask_price != None and valbz_ask_price != None and vale_bid_price != None and valbz_bid_price != None and valbz_ask_price < vale_bid_price):
                        exchange.send_add_message(order_id=ordID, symbol="VALBZ", dir=Dir.BUY, price=valbz_ask_price, size=trade_size)
                        ordID += 1
                        exchange.send_add_message(order_id=ordID, symbol="VALE", dir=Dir.SELL, price=vale_bid_price, size=trade_size)
                        ordID += 1
                        vale_in_hand -= trade_size

                    if (vale_ask_price != None and valbz_ask_price != None and vale_bid_price != None and valbz_bid_price != None and vale_ask_price < valbz_bid_price):
                        exchange.send_add_message(order_id=ordID, symbol="VALE", dir=Dir.BUY, price=vale_ask_price, size=trade_size)
                        ordID += 1
                        exchange.send_add_message(order_id=ordID, symbol="VALBZ", dir=Dir.SELL, price=valbz_bid_price, size=trade_size)
                        ordID += 1
                        vale_in_hand += trade_size

                if (vale_in_hand == 10):
                    exchange.send_convert_message(order_id=ordID, symbol="VALE", dir=Dir.SELL, size=10)
                elif (vale_in_hand == -10):
                    exchange.send_convert_message(order_id=ordID, symbol="VALE", dir=Dir.BUY, size=10)


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
