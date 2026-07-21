#!/usr/bin/env python3
"""RoboCopy GUI 测试"""
import os, sys, json, tempfile, shutil, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robocopy_gui import params_to_argv, argv_to_cmdstr, PRESETS, PARAM_FIELDS
import unittest

class TestParams(unittest.TestCase):
    def test_basic(self):
        p = {"src":r"C:\a","dst":r"D:\b","files":"*.*"}
        a = params_to_argv(p)
        self.assertIn(r"C:\a", a)
        self.assertIn(r"D:\b", a)
        self.assertIn("*.*", a)

    def test_mirror(self):
        a = params_to_argv({"src":"s","dst":"d","files":"*.*","mirror":True})
        self.assertIn("/MIR", a)

    def test_exclude(self):
        a = params_to_argv({"src":"s","dst":"d","files":"*.*","xf":"*.log *.tmp","xd":"t"})
        self.assertIn("/XF", a); self.assertIn("*.log", a)
        self.assertIn("/XD", a); self.assertIn("t", a)

    def test_presets(self):
        for name in PRESETS:
            self.assertIsInstance(PRESETS[name], dict)

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = os.path.join(tempfile.gettempdir(), "rc_test")
        cls.s = os.path.join(cls.d, "src")
        cls.t = os.path.join(cls.d, "dst")
        os.makedirs(cls.s, exist_ok=True)
        for i in range(3):
            with open(os.path.join(cls.s, f"f{i}.txt"), "w") as f:
                f.write("x"*500)
        os.makedirs(os.path.join(cls.s, "sub"), exist_ok=True)
        with open(os.path.join(cls.s, "sub", "s.txt"), "w") as f:
            f.write("sub")
        os.makedirs(cls.t, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_copy(self):
        r = subprocess.run(["robocopy",self.s,self.t,"*.*","/E","/R:0","/W:1","/NJH","/NJS"],
                          capture_output=True, text=True, timeout=30)
        self.assertIn(r.returncode, [0,1])
        for f in ["f0.txt","f1.txt","f2.txt"]:
            self.assertTrue(os.path.exists(os.path.join(self.t, f)))
        self.assertTrue(os.path.exists(os.path.join(self.t, "sub", "s.txt")))

    def test_mirror(self):
        with open(os.path.join(self.t,"extra.txt"),"w") as f: f.write("x")
        subprocess.run(["robocopy",self.s,self.t,"*.*","/MIR","/R:0","/W:1","/NJH","/NJS"],
                      capture_output=True, timeout=30)
        self.assertFalse(os.path.exists(os.path.join(self.t,"extra.txt")))

if __name__ == "__main__":
    suite = unittest.TestSuite()
    l = unittest.TestLoader()
    suite.addTests(l.loadTestsFromTestCase(TestParams))
    suite.addTests(l.loadTestsFromTestCase(TestIntegration))
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if r.wasSuccessful() else 1)
