import run


def test_run_module_defines_host_and_port():
    assert run.HOST == "127.0.0.1"
    assert run.PORT == 8000
