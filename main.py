import argparse
import logging
import sys
import time
from cmd import Cmd

from smartcard import util
from smartcard.CardRequest import CardRequest
from smartcard.CardType import AnyCardType
from smartcard.Exceptions import CardRequestTimeoutException

try:
    import readline
except ImportError:
    # readline version for windows
    import pyreadline as readline

NAME = 'NFC Shell'

_logger = logging.getLogger(NAME)
_logger.addHandler(logging.NullHandler())


class SmartCard:
    """
    Helper functions for using the smart card library.
    """

    @staticmethod
    def connect_to_chip(timeout, card_type=AnyCardType()):
        """
        Establish a connection with the first chip presented to the reader before the timeout.

        :param timeout: The number of seconds for a chip before timing out
        :param card_type: The card type to wait for
        :return: A connection to the chip or false if it the read times out.
        """
        try:
            _logger.debug('Entering SmartCard.connect_to_chip function.')
            connection = CardRequest(timeout=timeout, cardType=card_type).waitforcard().connection
            connection.connect()
            return connection
        except CardRequestTimeoutException as e:
            _logger.debug('Card connection timed out after {timeout} seconds.')
            return False
        except Exception as e:
            raise Exception('Card connection failed unexpectedly.') from e


class PN532:
    """
    Helper functions for using the PN532 module.
    """

    @staticmethod
    def in_communicate_thru_command(command_bytes):
        """
        Wraps commands with the inCommunicateThru prefix for the PN532 module.

        :param command_bytes: An array of HEX commands to transmit
        :return: The command with the inCommunicateThru prefix for the ACR122
        """
        _logger.debug('Entering PN532.in_communicate_thru_command function.')
        return [0xD4, 0x42] + command_bytes


class ACR122:
    """
    Helper functions for using the ACR122
    """

    @staticmethod
    def direct_transmit_command(command_bytes):
        """
        Wraps commands with the direct transmit prefix for the ACR122.

        :param command_bytes: An array of HEX commands to transmit
        :return: The command with the direct transmit prefix for the ACR122
        """
        _logger.debug('Entering ACR122.direct_transmit_command function.')
        return [0xFF, 0x00, 0x00, 0x00] + [len(command_bytes)] + command_bytes

    @staticmethod
    def transmit_raw_command(command_bytes, connection=None):
        """
        Handle command sending and exceptions for the ACR122.

        :param command_bytes: An array of HEX commands to transmit
        :param connection: The connection to use to transmit the commands over. Must have a `transmit` function.
        :return: A tuple of the data (array of hex digits) and a boolean representing the status of the command
        """
        _logger.debug('Entering ACR122.transmit_raw_command function.')
        try:
            # If connection is not set, create one
            if connection is None:
                connection = SmartCard.connect_to_chip(timeout=15)
            if connection is False:
                print(f'Chip connection timed out.')
                return [], False
            # Wrap commands in the required prefixes and postfixes for the ACR122
            command_bytes = PN532.in_communicate_thru_command(command_bytes)
            command_bytes = ACR122.direct_transmit_command(command_bytes)
            # Send the command
            data, sw1, sw2 = connection.transmit(command_bytes)
            _logger.debug(f'Data: {data}. sw1: {sw1}, sw2: {sw2}')
            # Parse results
            ok = (sw1 == 0x90) and (data[:3] == [0xD5, 0x43, 0x00])
            data = data[3:]
            return data, ok
        except RuntimeError as e:
            _logger.error(f'Error running the "{util.toHexString(command_bytes)}" command.', exc_info=True)
            return [], False


class NfcShell(Cmd):
    """
    The class to manage the CLI commands.
    """

    prompt = "> "
    use_rawinput = False

    def do_run(self, args, timeout=15):
        """
        Command handler for running a command once.

        :param args: args passed into the command. expects a string of commands in hex separated by a `;`
        :param timeout: how long to wait for the chip before executing the commands
        """
        _logger.debug('Entering NfcShell.do_run function.')

        # Connect to the reader
        connection = SmartCard.connect_to_chip(timeout=timeout)

        # Loop over each command
        commands = [util.toBytes(command) for command in args.split(";")]
        for command_bytes in commands:
            # Send command
            print(f'TX: "{util.toHexString(command_bytes)}"...')
            data, ok = ACR122.transmit_raw_command(command_bytes, connection)
            # Print output
            if ok:
                print(f'RX: (HEX)')
                print(util.toHexString(data))
                print(f'RX: (ASCII)')
                print(util.toASCIIString(data))
            else:
                print(f'"{util.toHexString(command_bytes)}" failed.')
                break

    def do_loop(self, args):
        """
        Command handler for running a command repeatedly.

        :param args: args passed into the command. expects a string of commands in hex separated by a `;`
        """
        _logger.debug('Entering NfcShell.do_loop function.')

        print('Press ctrl+c to return to the prompt...')
        # Loop
        count = 1
        while True:
            try:
                print(f'Run #{count}:')
                self.do_run(args, timeout=10)
                time.sleep(2)
                count += 1
            except KeyboardInterrupt:
                return

    def do_help(self, args):
        """
        Prints the help...

        :param args: args passed into the command. Expects nothing.
        """
        _logger.debug('Entering NfcShell.do_help function.')
        print('Read the README.md file perhaps?')

    def do_exit(self, args):
        """
        Exits the CLI

        :param args: args passed into the command. Expects nothing.
        """
        _logger.debug('Entering NfcShell.do_exit function.')
        exit(0)


def configure_logger(level):
    """
    Configure the NFC shell logger.
    Sends logs with a level of warnings or greater to go to STDERR.
    Sends logs with a level of info or lower to go to STDOUT.

    :param level: The log level
    """
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger().setLevel(level)
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(log_formatter)
    _logger.addHandler(stderr_handler)
    if level <= logging.INFO:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(level)
        stdout_handler.setFormatter(log_formatter)
        stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
        _logger.addHandler(stdout_handler)


def _main():
    """
    The main application code.
    """
    log_level = logging.DEBUG
    try:
        # Read in arguments
        arg_parser = argparse.ArgumentParser()
        arg_parser.add_argument(
            '-v', '--verbose',
            action='count',
            default=0,
            help='verbose log output'
        )
        program_args = arg_parser.parse_args()
        # Setup logging
        log_level = logging.WARNING - (10 * program_args.verbose)
        configure_logger(log_level)
        # Debug print of args
        for arg in vars(program_args):
            _logger.debug(f'Program argument "{program_args}" is set to "{arg}"')
        # Start CLI interface loop
        NfcShell().cmdloop(f'{NAME} CLI Application')
    except RuntimeError as e:
        # Handle fatal exceptions
        raise e
        cause = f', {e.__cause__}' if e.__cause__ is not None else ''
        _logger.critical(
            f'A fatal error occurred while running the {NAME} application: {e}{cause}',
            exc_info=(logging.DEBUG >= log_level)
        )
        exit(1)
    finally:
        print(f'Exiting {NAME}')


if __name__ == "__main__":
    _main()
