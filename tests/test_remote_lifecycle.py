from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from urllib.request import Request, urlopen

from PyQt6.QtCore import QCoreApplication

from src.ai_control.chat_message_log import ChatMessageLog
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

    def test_chat_message_pages_are_bounded_to_ten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = ChatMessageLog(root=Path(directory))
            for index in range(15):
                log.append(
                    "test-character",
                    {
                        "turn_id": str(index),
                        "side": "right",
                        "text": f"message-{index}",
                    },
                )

            latest_page, has_more = log.load_message_page("test-character", limit=10)
            older_page, older_has_more = log.load_message_page(
                "test-character",
                offset=len(latest_page),
                limit=10,
            )

        self.assertEqual(10, len(latest_page))
        self.assertEqual("message-5", latest_page[0]["text"])
        self.assertEqual("message-14", latest_page[-1]["text"])
        self.assertTrue(has_more)
        self.assertEqual(5, len(older_page))
        self.assertEqual("message-0", older_page[0]["text"])
        self.assertFalse(older_has_more)

    def test_manual_start_handshake_and_stop(self) -> None:
        received_messages: list[tuple[int, str]] = []
        history_requests: list[tuple[int, int, int]] = []

        def get_history(hwnd: int, offset: int, limit: int) -> tuple[list[dict[str, str]], bool]:
            history_requests.append((hwnd, offset, limit))
            return [{"id": "turn-1:right", "text": f"history:{hwnd}"}], False

        self.manager.set_remote_handlers(
            on_message=lambda hwnd, text: received_messages.append((hwnd, text)) or True,
            get_history=get_history,
            capture_frame=lambda hwnd: f"frame:{hwnd}".encode("utf-8"),
        )
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
        self.assertIsNone(session["target"])
        self.assertEqual(DEFAULT_PERMISSIONS, session["permissions"])
        self.assertEqual(1, len(self.manager.snapshot().sessions))

        bind_request = Request(
            f"{snapshot.endpoint}/sessions/{session['session_id']}/target",
            data=json.dumps({"target_hwnd": self.target.hwnd}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {session['session_id']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(bind_request, timeout=2.0) as response:
            bound_session = json.loads(response.read().decode("utf-8"))
        self.assertEqual(self.target.hwnd, bound_session["target"]["hwnd"])

        messages_url = f"{snapshot.endpoint}/sessions/{session['session_id']}/messages"
        session_headers = {"Authorization": f"Bearer {session['session_id']}"}
        with urlopen(Request(f"{messages_url}?offset=0&limit=50", headers=session_headers), timeout=2.0) as response:
            history = json.loads(response.read().decode("utf-8"))
        self.assertEqual("history:12345", history["messages"][0]["text"])
        self.assertFalse(history["has_more"])
        self.assertEqual([(self.target.hwnd, 0, 10)], history_requests)

        send_request = Request(
            messages_url,
            data=json.dumps({"text": "Open inventory"}).encode("utf-8"),
            headers={**session_headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(send_request, timeout=2.0) as response:
            self.assertEqual(202, response.status)
        self.assertEqual([(self.target.hwnd, "Open inventory")], received_messages)

        with urlopen(
            Request(
                f"{snapshot.endpoint}/sessions/{session['session_id']}/frame",
                headers=session_headers,
            ),
            timeout=2.0,
        ) as response:
            self.assertEqual("image/jpeg", response.headers["Content-Type"])
            self.assertEqual(b"frame:12345", response.read())

        second_target = SimpleNamespace(
            hwnd=54321,
            pid=987,
            window_title="Second Game",
            process_name="second.exe",
            creation_time="2026-10-25T01:00:00Z",
        )
        self.manager.set_targets([self.target, second_target])
        rebind_request = Request(
            f"{snapshot.endpoint}/sessions/{session['session_id']}/target",
            data=json.dumps({"target_hwnd": second_target.hwnd}).encode("utf-8"),
            headers={**session_headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(rebind_request, timeout=2.0) as response:
            rebound_session = json.loads(response.read().decode("utf-8"))
        self.assertEqual(second_target.hwnd, rebound_session["target"]["hwnd"])

        legacy_payload = json.dumps(
            {
                "username": credentials.username,
                "password": credentials.password,
                "device_name": "Legacy client",
                "target_hwnd": self.target.hwnd,
            }
        ).encode("utf-8")
        legacy_request = Request(
            f"{snapshot.endpoint}/handshake",
            data=legacy_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(legacy_request, timeout=2.0) as response:
            legacy_session = json.loads(response.read().decode("utf-8"))
        self.assertEqual(self.target.hwnd, legacy_session["target"]["hwnd"])

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
