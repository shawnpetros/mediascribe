class Mediascribe < Formula
  desc "TUI-first tool for transcribing, translating, and analyzing audio/video media"
  homepage "https://github.com/shawnpetros/mediascribe"
  url "https://files.pythonhosted.org/packages/08/dd/1389d7c37499a3ec7100defffcde87a3850855e5120660fcbaa037c0bd26/mediascribe-0.2.1.tar.gz"
  sha256 "d77cedb36984fcb98da2adfbcee7e59cd94d1d2dbfe1908ff82fb5aadf919d2b"
  license "MIT"
  head "https://github.com/shawnpetros/mediascribe.git", branch: "main"

  depends_on "ffmpeg"
  depends_on "python@3.13"

  def install
    python3 = "python3.13"
    venv = libexec/"venv"
    system python3, "-m", "venv", venv
    system venv/"bin/pip", "install", "--upgrade", "pip"
    system venv/"bin/pip", "install", cached_download
    bin.install_symlink venv/"bin/mediascribe"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/mediascribe --version")
  end
end
