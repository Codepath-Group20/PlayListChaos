from src.app import main


def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert "Hello, CodePath A110!" in captured.out
