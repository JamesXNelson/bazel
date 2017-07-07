# pylint: disable=g-bad-file-header
# Copyright 2017 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import stat
import unittest
from src.test.py.bazel import test_base


class LauncherScriptTest(test_base.TestBase):

  def testJavaBinaryLauncher(self):
    self.ScratchFile('WORKSPACE')
    self.ScratchFile('foo/BUILD', [
        'java_binary(',
        '  name = "foo",',
        '  srcs = ["Main.java"],',
        '  main_class = "Main",',
        '  data = ["//bar:bar.txt"],',
        ')',
    ])
    self.ScratchFile('foo/Main.java', [
        'public class Main {',
        '  public static void main(String[] args) {'
        '    System.out.println("hello java");',
        '  }',
        '}',
    ])
    self.ScratchFile('bar/BUILD', ['exports_files(["bar.txt"])'])
    self.ScratchFile('bar/bar.txt', ['hello'])

    exit_code, stdout, stderr = self.RunBazel(['info', 'bazel-bin'])
    self.AssertExitCode(exit_code, 0, stderr)
    bazel_bin = stdout[0]

    exit_code, _, stderr = self.RunBazel(['build', '//foo'])
    self.AssertExitCode(exit_code, 0, stderr)
    main_binary = os.path.join(bazel_bin,
                               'foo/foo%s' % ('.cmd'
                                              if self.IsWindows() else ''))
    self.assertTrue(os.path.isfile(main_binary))
    self.assertTrue(os.path.isdir(os.path.join(bazel_bin, 'foo/foo.runfiles')))

    if self.IsWindows():
      self.assertTrue(os.path.isfile(main_binary))
      self.AssertRunfilesManifestContains(
          os.path.join(bazel_bin, 'foo/foo.runfiles/MANIFEST'),
          '__main__/bar/bar.txt')
    else:
      self.assertTrue(
          os.path.islink(
              os.path.join(bazel_bin, 'foo/foo.runfiles/__main__/bar/bar.txt')))

    exit_code, stdout, stderr = self.RunProgram([main_binary])
    self.AssertExitCode(exit_code, 0, stderr)
    self.assertEqual(stdout[0], 'hello java')

  def testShBinaryLauncher(self):
    self.ScratchFile('WORKSPACE')
    self.ScratchFile(
        'foo/BUILD',
        [
            # On Linux/MacOS, all sh_binary rules generate an output file with
            # the same name as the rule, and this is a symlink to the file in
            # `srcs`. (Bazel allows only one file in `sh_binary.srcs`.)
            # On Windows, if the rule's name and the srcs's name end with the
            # same extension, and this extension is one of ".exe", ".cmd", or
            # ".bat", then sh_binary makes a copy of the output file, with the
            # same name as the rule. Otherwise (if the rule's name doesn't end
            # with such an extension, or the extension of it doesn't match the
            # main file's) then Bazel creates a %{rulename}.cmd output which is
            # a similar launcher script to that generated by java_binary rules.
            'sh_binary(',
            '  name = "bin1.sh",',
            '  srcs = ["foo.sh"],',
            '  data = ["//bar:bar.txt"],',
            ')',
            'sh_binary(',
            '  name = "bin2.cmd",',  # name's extension matches that of srcs[0]
            '  srcs = ["foo.cmd"],',
            '  data = ["//bar:bar.txt"],',
            ')',
            'sh_binary(',
            '  name = "bin3.bat",',  # name's extension doesn't match srcs[0]'s
            '  srcs = ["foo.cmd"],',
            '  data = ["//bar:bar.txt"],',
            ')',
        ])
    foo_sh = self.ScratchFile('foo/foo.sh', [
        '#!/bin/bash',
        'echo hello shell',
    ])
    foo_cmd = self.ScratchFile('foo/foo.cmd', ['@echo hello batch'])
    self.ScratchFile('bar/BUILD', ['exports_files(["bar.txt"])'])
    self.ScratchFile('bar/bar.txt', ['hello'])
    os.chmod(foo_sh, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    os.chmod(foo_cmd, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    exit_code, stdout, stderr = self.RunBazel(['info', 'bazel-bin'])
    self.AssertExitCode(exit_code, 0, stderr)
    bazel_bin = stdout[0]

    exit_code, _, stderr = self.RunBazel(['build', '//foo:all'])
    self.AssertExitCode(exit_code, 0, stderr)

    bin1 = os.path.join(bazel_bin, 'foo', 'bin1.sh.cmd'
                        if self.IsWindows() else 'bin1.sh')
    self.assertTrue(os.path.exists(bin1))
    self.assertTrue(
        os.path.isdir(os.path.join(bazel_bin, 'foo/bin1.sh.runfiles')))

    bin2 = os.path.join(bazel_bin, 'foo/bin2.cmd')
    self.assertTrue(os.path.exists(bin2))
    self.assertTrue(
        os.path.isdir(os.path.join(bazel_bin, 'foo/bin2.cmd.runfiles')))

    bin3 = os.path.join(bazel_bin, 'foo', 'bin3.bat.cmd'
                        if self.IsWindows() else 'bin3.bat')
    self.assertTrue(os.path.exists(bin3))
    self.assertTrue(
        os.path.isdir(os.path.join(bazel_bin, 'foo/bin3.bat.runfiles')))

    if self.IsWindows():
      self.assertTrue(os.path.isfile(bin1))
      self.assertTrue(os.path.isfile(bin2))
      self.assertTrue(os.path.isfile(bin3))
    else:
      self.assertTrue(os.path.islink(bin1))
      self.assertTrue(os.path.islink(bin2))
      self.assertTrue(os.path.islink(bin3))

    if self.IsWindows():
      self.AssertRunfilesManifestContains(
          os.path.join(bazel_bin, 'foo/bin1.sh.runfiles/MANIFEST'),
          '__main__/bar/bar.txt')
      self.AssertRunfilesManifestContains(
          os.path.join(bazel_bin, 'foo/bin2.cmd.runfiles/MANIFEST'),
          '__main__/bar/bar.txt')
      self.AssertRunfilesManifestContains(
          os.path.join(bazel_bin, 'foo/bin3.bat.runfiles/MANIFEST'),
          '__main__/bar/bar.txt')
    else:
      self.assertTrue(
          os.path.islink(
              os.path.join(bazel_bin,
                           'foo/bin1.sh.runfiles/__main__/bar/bar.txt')))
      self.assertTrue(
          os.path.islink(
              os.path.join(bazel_bin,
                           'foo/bin2.cmd.runfiles/__main__/bar/bar.txt')))
      self.assertTrue(
          os.path.islink(
              os.path.join(bazel_bin,
                           'foo/bin3.bat.runfiles/__main__/bar/bar.txt')))

    exit_code, stdout, stderr = self.RunProgram([bin1])
    self.AssertExitCode(exit_code, 0, stderr)
    self.assertEqual(stdout[0], 'hello shell')

    if self.IsWindows():
      exit_code, stdout, stderr = self.RunProgram([bin2])
      self.AssertExitCode(exit_code, 0, stderr)
      self.assertEqual(stdout[0], 'hello batch')

      exit_code, stdout, stderr = self.RunProgram([bin3])
      self.AssertExitCode(exit_code, 0, stderr)
      self.assertEqual(stdout[0], 'hello batch')

  def AssertRunfilesManifestContains(self, manifest, entry):
    with open(manifest, 'r') as f:
      for l in f:
        tokens = l.strip().split(' ', 1)
        if len(tokens) == 2 and tokens[0] == entry:
          return
    self.fail('Runfiles manifest "%s" did not contain "%s"' % (manifest, entry))


if __name__ == '__main__':
  unittest.main()