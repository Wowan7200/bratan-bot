{ pkgs }: {
  deps = [
    pkgs.ffmpeg
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
    pkgs.python311Packages.requests
    pkgs.python311Packages.pydub
    pkgs.python311Packages.speechrecognition
    pkgs.python311Packages.flask
    pkgs.python311Packages.pyTelegramBotAPI
  ];
}
