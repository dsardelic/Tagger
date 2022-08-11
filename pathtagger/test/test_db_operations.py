"""
    @parameterized.expand(
        [
            ("empty name", "", "#AB3456", 3),
            ("empty color", "New tag", "", 4),
            ("name and color", "New tag", "#AB3456", 4),
            ("name already exists", "Videos", "#AB3456", 3),
        ]
    )
    def test_add_tag(self, _, name, color):
"""
