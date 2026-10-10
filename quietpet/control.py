# -*- coding: utf-8 -*-
"""Localhost control channel: lets the MCP bridge drive the running GUI.

The GUI runs a tiny line-delimited JSON server on 127.0.0.1. Requests are
handed to the Tk main thread (via a queue) and answers are written back.
"""
import json
import queue
import socket
import threading

from .core.config import CONTROL_PORT

HOST = '127.0.0.1'


class ControlServer:
    def __init__(self, handler, port=None):
        self.handler = handler            # handler(cmd, args) -> dict (main thread)
        self.port = int(port or CONTROL_PORT)
        self._sock = None
        self._stop = False
        self._queue = queue.Queue()

    def start(self):
        threading.Thread(target=self._serve, name='QuietPetControl', daemon=True).start()

    def _serve(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, self.port))
            s.listen(8)
        except OSError:
            return
        self._sock = s
        while not self._stop:
            try:
                conn, _ = s.accept()
            except OSError:
                break
            threading.Thread(target=self._conn, args=(conn,), daemon=True).start()

    def _conn(self, conn):
        try:
            f = conn.makefile('rwb')
            for raw in f:
                try:
                    req = json.loads(raw.decode('utf-8'))
                except Exception:
                    continue
                box, event = {}, threading.Event()
                self._queue.put((req, box, event))
                event.wait(5.0)
                resp = box.get('resp', {'ok': False, 'error': 'timeout'})
                f.write((json.dumps(resp, ensure_ascii=False) + '\n').encode('utf-8'))
                f.flush()
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def pump(self):
        """Run pending requests on the Tk thread. Call from an ``after`` tick."""
        while True:
            try:
                req, box, event = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                box['resp'] = self.handler(req.get('cmd'), req.get('args') or {})
            except Exception as exc:
                box['resp'] = {'ok': False, 'error': repr(exc)}
            event.set()

    def stop(self):
        self._stop = True
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass


def send_command(cmd, args=None, port=None, timeout=5.0):
    """Send one command to the running GUI; returns the reply dict."""
    port = int(port or CONTROL_PORT)
    with socket.create_connection((HOST, port), timeout=timeout) as s:
        s.sendall((json.dumps({'cmd': cmd, 'args': args or {}}) + '\n').encode('utf-8'))
        line = s.makefile('rb').readline()
    if not line:
        return {'ok': False, 'error': 'no response'}
    return json.loads(line.decode('utf-8'))
