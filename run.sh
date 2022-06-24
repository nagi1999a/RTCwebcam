#!/bin/sh
CERT_PATH=./data/cert.cert
NUM_DEVICES=2
CARD_LABELS="Reserved Device 0,RTCwebcam Device 1"
EXCLUSIVE_CAPS="1,1"

if [ -f "$CERT_PATH" ]; then
    echo "Certificate exists, Skip generating.\n"
else
    echo "Generating certificate...\n"
    openssl req -new -x509 -nodes -days 365 -subj "/C=US/ST=California/L=San Francisco/O=Example/CN=localhost" -keyout $CERT_PATH -out $CERT_PATH
fi

if [ $? -eq 0 ]; then
    echo "Certificate generated successfully.\n"
else
    echo "Certificate generation failed, is openssl installed?\n"
    exit 1
fi

if [ $(lsmod | grep v4l2loopback | wc -l) -eq 0 ]; then
    echo "Loading v4l2loopback module...\n"
    sudo modprobe v4l2loopback devices=$NUM_DEVICES exclusive_caps=$EXCLUSIVE_CAPS card_label="$CARD_LABELS"
else 
    echo "v4l2loopback module already loaded."
    echo "To avoid errors, it is recommended to reload v4l2loopback before running this script."
    read -r -p "Do you want to reload it? [y/N] " RELOAD_MODULE
    if [ "$RELOAD_MODULE" = "y" ]; then
        sudo rmmod v4l2loopback
        if [ $? -eq 0 ]; then
            echo "v4l2loopback module unloaded successfully."
        else
            echo "v4l2loopback module reload failed.\n"
            exit 1
        fi
        sudo modprobe v4l2loopback devices=$NUM_DEVICES exclusive_caps=$EXCLUSIVE_CAPS card_label="$CARD_LABELS"
    fi
fi
if [ $? -eq 0 ]; then
    echo "v4l2loopback module loaded successfully.\n"
else
    echo "v4l2loopback module loading failed.\n"
    exit 1
fi

# test the first argument equals to "--debug"
if [ "$1" = "--debug" ]; then
    python server.py
else
    python server.py 2>/dev/null
fi
