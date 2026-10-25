from __future__ import annotations

import json
import time
import unittest
from types import SimpleNamespace
from urllib.request import Request, urlopen

from PyQt6.QtCore import QCoreApplication

from remote.src.application import RemoteServerLifecycleManager
from remote.src.domain import DEFAULT_PERMISSIONS, RemoteServerState


class RemoteLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self) -> None:
        self.manager = RemoteServerLifecycleManager(host="127.0.0.1", port=0)
        self.target = SimpleNamespace(
            hwnd=12345,
            pid=678,
            window_title="MU GameThuVN (Server - Character)",
            process_name="main.exe",
            creation_time="2026-10-25T00:00:00Z",
        )

    def tearDown(self) -> None:
        self.manager.shutdown()
        self._pump_events()

    def test_start_requires_selected_target(self) -> None:
        self.assertFalse(self.manager.start())
        snapshot = self.manager.snapshot()
        self.assertEqual(RemoteServerState.STOPPED, snapshot.state)
        self.assertIn("ít nhất một game window", snapshot.error)

    def test_manual_start_handshake_and_stop(self) -> None:
        self.manager.set_targets([self.target])
        self.assertTrue(self.manager.start())
        self.assertTrue(self._wait_for(RemoteServerState.RUNNING))
        snapshot = self.manager.snapshot()
        self.assertTrue(snapshot.endpoint.startswith("http://127.0.0.1:"))
        self.assertIsNotNone(snapshot.credentials)

        credentials = snapshot.credentials
        payload = json.dumps(
            {
                "username": credentials.username,
                "password": credentials.password,
                "device_name": "Android test",
                "target_hwnd": self.target.hwnd,
            }
        ).encode("utf-8")
        request = Request(
            f"{snapshot.endpoint}/handshake",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2.0) as response:
            session = json.loads(response.read().decode("utf-8"))
        self.assertEqual("Android test", session["device_name"])
        self.assertEqual(DEFAULT_PERMISSIONS, session["permissions"])
        self.assertEqual(1, len(self.manager.snapshot().sessions))

        self.assertTrue(self.manager.stop())
        self.assertTrue(self._wait_for(RemoteServerState.STOPPED))
        self.assertIsNone(self.manager.snapshot().credentials)

    def test_cancel_start_returns_stopped(self) -> None:
        self.manager.set_targets([self.target])
        self.assertTrue(self.manager.start())
        self.assertTrue(self.manager.cancel_operation())
        self.assertTrue(self._wait_for(RemoteServerState.STOPPED))

    def test_cancel_stop_returns_running(self) -> None:
        self.manager.set_targets([self.target])
        self.assertTrue(self.manager.start())
        self.assertTrue(self._wait_for(RemoteServerState.RUNNING))
        credentials = self.manager.snapshot().credentials
        self.assertTrue(self.manager.stop())
        self.assertTrue(self.manager.cancel_operation())
        self.assertTrue(self._wait_for(RemoteServerState.RUNNING))
        self.assertEqual(credentials, self.manager.snapshot().credentials)

    def test_removing_last_target_does_not_stop_server(self) -> None:
        self.manager.set_targets([self.target])
        self.assertTrue(self.manager.start())
        self.assertTrue(self._wait_for(RemoteServerState.RUNNING))
        self.manager.set_targets([])
        self.assertEqual(RemoteServerState.RUNNING, self.manager.state)
        self.assertEqual((), self.manager.snapshot().targets)

    def test_shutdown_during_stop_cannot_restore_running_state(self) -> None:
        self.manager.set_targets([self.target])
        self.assertTrue(self.manager.start())
        self.assertTrue(self._wait_for(RemoteServerState.RUNNING))
        self.assertTrue(self.manager.stop())
        self.manager.shutdown()
        time.sleep(0.45)
        self._pump_events()
        self.assertEqual(RemoteServerState.STOPPED, self.manager.state)

    def _wait_for(self, state: RemoteServerState, timeout: float = 3.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._pump_events()
            if self.manager.state == state:
                return True
            time.sleep(0.01)
        return False

    @classmethod
    def _pump_events(cls) -> None:
        cls.app.processEvents()


if __name__ == "__main__":
    unittest.main()
