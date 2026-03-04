class Mediascribe < Formula
  desc "TUI-first tool for transcribing, translating, and analyzing audio/video media"
  homepage "https://github.com/shawnpetros/mediascribe"
  url "https://files.pythonhosted.org/packages/91/f7/e98a7dcec85cfd6112cc6d4d1e63f502d0004de19671d2e8d37bd7d01743/mediascribe-0.9.0.tar.gz"
  sha256 "177e6f7ce2e3df281ec76ca1c9f5f2a032b48af633132e7a0766287a89820378"
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
