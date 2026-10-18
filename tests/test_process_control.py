"""Failure-focused tests for Windows process ownership without killing real tasks."""
import importlib
from pathlib import Path
import subprocess
from unittest.mock import Mock
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def common(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    return importlib.import_module('common')


def owned_process():
    process = Mock(pid=12345)
    process.poll.return_value = None
    process.wait.return_value = 0
    return process


def test_windows_stops_workers_gracefully_without_terminateprocess(common, monkeypatch):
    monkeypatch.setattr(common, 'WINDOWS', True)
    process = owned_process()
    common.stop_owned_process(process)
    process.send_signal.assert_called_once()
    process.terminate.assert_not_called()
    process.kill.assert_not_called()


@pytest.mark.parametrize('failure', [OSError('console unavailable'), subprocess.TimeoutExpired('service', 8)])
def test_windows_fallback_targets_owned_tree_and_never_all_python(common, monkeypatch, failure):
    monkeypatch.setattr(common, 'WINDOWS', True)
    process = owned_process()
    if isinstance(failure, subprocess.TimeoutExpired):
        process.wait.side_effect = [failure, 0]
    else:
        process.send_signal.side_effect = failure
    runner = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(common.subprocess, 'run', runner)
    common.stop_owned_process(process)
    arguments = runner.call_args.args[0]
    assert arguments[1:] == ['/PID', '12345', '/T', '/F']
    assert '/IM' not in arguments
    process.terminate.assert_not_called()


def test_stop_failure_is_reported_and_process_ownership_is_retained(common, monkeypatch):
    monkeypatch.setattr(common, 'WINDOWS', True)
    process = owned_process()
    process.send_signal.side_effect = OSError('no console')
    monkeypatch.setattr(common.subprocess, 'run', Mock(return_value=Mock(returncode=1)))
    owner = common.ServiceProcesses()
    owner.processes['payment'] = process
    with pytest.raises(RuntimeError, match='owned service process tree'):
        owner.stop('payment')
    assert owner.processes['payment'] is process


def test_already_exited_process_is_not_signaled_by_reused_pid(common, monkeypatch):
    monkeypatch.setattr(common, 'WINDOWS', True)
    process = owned_process()
    process.poll.return_value = 0
    common.stop_owned_process(process)
    process.send_signal.assert_not_called()


def test_linux_shutdown_still_uses_sigterm(common, monkeypatch):
    monkeypatch.setattr(common, 'WINDOWS', False)
    process = owned_process()
    common.stop_owned_process(process)
    process.terminate.assert_called_once()
    process.send_signal.assert_not_called()


def test_windows_launches_in_separate_console_group_and_strips_admin_secret(common, monkeypatch, tmp_path):
    monkeypatch.setattr(common, 'WINDOWS', True)
    monkeypatch.setattr(common, 'ROOT', tmp_path)
    monkeypatch.setattr(common, 'config', lambda _: {'HOST':'127.0.0.1', 'PORT':'0', 'DATABASE_URL':'own-role'})
    monkeypatch.setenv('HOTEL_ADMIN_DATABASE_URL', 'admin-secret')
    spawn = Mock(return_value=owned_process())
    monkeypatch.setattr(common.subprocess, 'Popen', spawn)
    owner = common.ServiceProcesses()
    monkeypatch.setattr(owner, 'wait_healthy', lambda _: None)
    owner.start('payment')
    assert spawn.call_args.kwargs['creationflags'] != 0
    assert spawn.call_args.kwargs['env']['DATABASE_URL'] == 'own-role'
    assert 'HOTEL_ADMIN_DATABASE_URL' not in spawn.call_args.kwargs['env']
    owner.handles['payment'].close()


def test_cleanup_attempts_other_owned_services_after_one_stop_failure(common, monkeypatch):
    owner = common.ServiceProcesses()
    owner.processes = {'inventory':owned_process(), 'payment':owned_process()}
    calls = []
    def stop(name):
        calls.append(name)
        if name == 'inventory':
            raise RuntimeError('stop failed')
    monkeypatch.setattr(owner, 'stop', stop)
    with pytest.raises(RuntimeError, match='inventory'):
        owner.close()
    assert calls == ['inventory', 'payment']
