#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <iostream>
#include <string>
#include <cstdlib>
#include <exception>
#include <tuple>


std::tuple<double, double, double> read_arduino(){
        // Change this to your Arduino's COM port.
    const char* portName = "\\\\.\\COM6";
    const DWORD baudRate = CBR_115200;

    // Open the serial port.
    HANDLE serial = CreateFileA(
        portName,
        GENERIC_READ | GENERIC_WRITE,
        0,
        nullptr,
        OPEN_EXISTING,
        0,
        nullptr
    );

    if (serial == INVALID_HANDLE_VALUE) {
        std::cerr << "Error: Could not open " << portName
                  << ". Check the COM port and try again.\n";
        return {0,0,0};
    }

    // Configure serial communication.
    DCB settings{};
    settings.DCBlength = sizeof(settings);

    if (!GetCommState(serial, &settings)) {
        std::cerr << "Error reading serial settings.\n";
        CloseHandle(serial);
        return {0, 0, 0};
    }

    settings.BaudRate = baudRate;
    settings.ByteSize = 8;
    settings.Parity   = NOPARITY;
    settings.StopBits = ONESTOPBIT;
    settings.fBinary  = TRUE;
    settings.fDtrControl = DTR_CONTROL_ENABLE;

    if (!SetCommState(serial, &settings)) {
        std::cerr << "Error configuring serial port.\n";
        CloseHandle(serial);
        return {0,0,0};
    }

    // Avoid blocking forever when no data is available.
    COMMTIMEOUTS timeouts{};
    timeouts.ReadIntervalTimeout = 50;
    timeouts.ReadTotalTimeoutConstant = 50;
    timeouts.ReadTotalTimeoutMultiplier = 10;

    if (!SetCommTimeouts(serial, &timeouts)) {
        std::cerr << "Error setting serial timeouts.\n";
        CloseHandle(serial);
        return {0,0,0};
    }

    // Discard stale data from before the connection.
    PurgeComm(serial, PURGE_RXCLEAR | PURGE_TXCLEAR);



    std::string line;
    char buffer[256];

    while (true) {
        DWORD bytesRead = 0;

        if (!ReadFile(
                serial, buffer, sizeof(buffer),
                &bytesRead, nullptr)) {
            std::cerr << "Serial read error.\n";
            break;
        }

        for (DWORD i = 0; i < bytesRead; ++i) {
            char ch = buffer[i];

            if (ch == '\n') {
                // Remove a trailing carriage return, if present.
                if (!line.empty() && line.back() == '\r') {
                    line.pop_back();
                }

                if (!line.empty()) {
                    try {
                        std::size_t used = 0;
                        double value = std::stod(line, &used);

                    } catch (const std::exception&) {
                        std::cerr << "Invalid data: "
                                  << line << '\n';
                    }
                }

                line.clear();
            } else {
                // Prevent a corrupted stream from growing indefinitely.
                if (line.size() < 128) {
                    line += ch;
                } else {
                    line.clear();
                }
            }
        }
    }

    double value1,value2,value3;
    value1 = std::stod(line.substr(0,3));
    value2 = std::stod(line.substr(4,8));
    value3 = std::stod(line.substr(9,12));

    CloseHandle(serial);
    return {value1,value2,value3};
}





int main(){
    read_arduino();
    return 0;
}

