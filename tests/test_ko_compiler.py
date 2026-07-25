import unittest

from ko_compiler import compile_ko_source


class KoCompilerTests(unittest.TestCase):
    def test_simple_declaration_and_print(self):
        source = 'int(10)*x\nprint(x)\n'
        code = compile_ko_source(source)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(namespace["x"], 10)

    def test_if_statement(self):
        source = 'int(4)*x\nif(x > 2) [\n    print("big")\n]\n'
        code = compile_ko_source(source)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(namespace["x"], 4)

    def test_class_and_method_syntax(self):
        source = 'Hero !class [\n    @private [\n        setup_player() [\n            print("hi")\n        ]\n    ]\n]\n*Hero*p1\n$p1*setup_player()\n'
        code = compile_ko_source(source)
        namespace = {}
        exec(code, namespace)
        self.assertIn("Hero", namespace)
        self.assertIn("p1", namespace)

    def test_import_random_syntax(self):
        source = '**Import**($Random)@also%*random!`global`:random\nint(<$random>(1, 3))*value\n'
        code = compile_ko_source(source)
        namespace = {}
        exec(code, namespace)
        self.assertIn("random", namespace)
        self.assertIn("value", namespace)
        self.assertTrue(1 <= namespace["value"] <= 3)

    def test_main_function_is_called(self):
        source = 'main() [\n    print("hello from main")\n]\n'
        code = compile_ko_source(source)
        namespace = {}
        exec(code, namespace)
        self.assertIn("main", namespace)

    def test_loop_syntax(self):
        source = 'int(0)*x\nloop(x < 3) [\n    x = x + 1\n]\n'
        code = compile_ko_source(source)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(namespace["x"], 3)

    def test_import_math_syntax(self):
        source = '**Import**($Math) [\n]\nint(math.sqrt(16))*value\n'
        code = compile_ko_source(source)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(namespace["value"], 4.0)

    def test_function_parameters(self):
        source = 'add(x, y) [\n    <now>(x + y)>result\n]\nadd(2, 3)\n'
        code = compile_ko_source(source)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(namespace["result"], 5)

    def test_version_1_3_main_block_class_and_index_syntax(self):
        source = """**Import**($Random)@also%*random!`global`:random
Hero !class [
    @private [
        string("A")*name
        int(100)*hp
        ('Kiem', 'Khien')*inventory

        use_item() [
            int(1)*item_index
            <printf>^("{name}:{inventory<{item_index}>}:{hp}")
        ]
    ]
]
[
    *Hero*p1
    $p1*use_item()
]
"""
        code = compile_ko_source(source, enforce_main=True)
        namespace = {}
        exec(code, namespace)
        self.assertIn("p1", namespace)

    def test_input_declaration_and_booling_syntax(self):
        source = 'booling(\\True\\)*enabled\n<input>("Name: ")&=string("")*name\n'
        code = compile_ko_source(source)
        self.assertIn("enabled = bool(True)", code)
        self.assertIn("name = input(\"Name: \")", code)


if __name__ == "__main__":
    unittest.main()
