class Mediascribe < Formula
  include Language::Python::Virtualenv

  desc "TUI-first tool for transcribing, translating, and analyzing audio/video media"
  homepage "https://github.com/shawnpetros/mediascribe"
  url "https://pypi.io/packages/source/m/mediascribe/mediascribe-0.1.0.tar.gz"
  sha256 "61cdd7569cfa994f3c30cc549e1d63b5b11676e973392de0b269b0f0886bec60"
  license "MIT"
  head "https://github.com/shawnpetros/mediascribe.git", branch: "main"

  depends_on "python@3.12"
  depends_on "ffmpeg"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/mediascribe --version")
  end
end
