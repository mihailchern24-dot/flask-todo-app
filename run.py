#!/usr/bin/env python3
"""Точка входа для запуска приложения"""
from app import APP, socketio

if __name__ == '__main__':
    socketio.run(APP, debug=True, host='0.0.0.0', port=5000)