#pragma once

#include <cstdint>

constexpr int HIGH = 1;
constexpr int LOW = 0;
constexpr int INPUT_PULLUP = 2;
constexpr int OUTPUT = 3;
constexpr int A0 = 14;
constexpr int A1 = 15;
constexpr int A2 = 16;
constexpr int A3 = 17;
constexpr int A4 = 18;
constexpr int A5 = 19;

inline void pinMode(int, int) {}
inline int digitalRead(int) { return LOW; }
inline void digitalWrite(int, int) {}
inline void delayMicroseconds(unsigned int) {}
inline unsigned long millis() { return 0; }
inline unsigned long micros() { return 0; }

struct SerialStub {
  void begin(unsigned long) {}
  int available() { return 0; }
  int read() { return 0; }
};

inline SerialStub Serial;
inline SerialStub Serial1;
