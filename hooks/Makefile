# Makefile for Kea Packet Logger Hook

# Adjust these paths if kea-config is not in your path or headers are elsewhere
KEA_CONFIG ?= kea-config
CXX = g++
CXXFLAGS = -I/usr/include/kea -fpic -shared -std=c++11

# Try to use kea-config if available for cflags
ifneq (, $(shell which $(KEA_CONFIG) 2>/dev/null))
    CXXFLAGS += $(shell $(KEA_CONFIG) --cflags)
    LDFLAGS += $(shell $(KEA_CONFIG) --libs)
endif

TARGET = libdhcp_logger.so
SOURCES = logger_hook.cc

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SOURCES) $(LDFLAGS)

clean:
	rm -f $(TARGET)
