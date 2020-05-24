# Python NFC Shell

This project is a simple NFC Shell application designed for use with the ACR122 USB NFC reader (Although it may work with other readers and the support will be expanded)

Disclaimer: 
I wrote this project rapidly for personal use, no effort has been made to test it extensively. I do plan on improving this tool if there is interest but either way use at your own risk.

## Warning

This application sends raw commands to your NFC chip. This can result in loss of functionality or the complete bricking of the chip. I am not the boss of you but I would not use this tool with a chip I can not afford to loose unless I was very familiar with the dataa sheet of the chip in question.

## Installation

Install python > 3.0  and install `pyscard` and `pyreadline`. `pip` seems to have issues with installing `pyscard` I had luck with the MSIs from the `pyscard` creator on [AppVeyor](https://ci.appveyor.com/project/LudovicRousseau/pyscard)

## Usage

Currently the application is only a CLI and auto picks the first reader it detects. (GUI and multiple reader support is intended)

Simply run `python main.py` from the repository to run the application. (Proper installation is intended)

### Hex String Formatting

HEX commands are written as string in 2 digit pairs. Multiple commands can be separated by a `;`, the commands will then be sent one at a time until they are finished or an error occurs.

**Examples:**
```
60
```
```
60; 30 FF;
```

### `RUN` command

The run command waits up to 15 seconds for a chip to be presented to the reader before executing the command sequence once

**Examples:**
```
run 60
```
```
run 60; 30 FF;
```

### `LOOP` command

The loop command waits up to 300 seconds for a chip to be presented to the reader before executing the command sequence, it then pauses for 2 seconds and repeats until `ctrl+c` is pressed. This is intended for batch processing of chips.

**Examples:**
```
loop 60
```
```
loop 60; 30 FF;
```

### `HELP` command

Outputs a message to read this file... 

### `EXIT` command 

Exits the application

