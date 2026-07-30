import unittest

from ..permissions import is_group_umo_allowed, normalize_allowed_umos


class UmoPermissionTests(unittest.TestCase):
    def test_normalize_allowlist(self):
        self.assertEqual(
            normalize_allowed_umos(
                [
                    " tata:GroupMessage:10001 ",
                    "",
                    "tata:GroupMessage:10001",
                    "tata:GroupMessage:10002",
                ]
            ),
            frozenset(
                {
                    "tata:GroupMessage:10001",
                    "tata:GroupMessage:10002",
                }
            ),
        )

    def test_exact_group_umo_is_allowed(self):
        allowed = normalize_allowed_umos(["tata:GroupMessage:10001"])
        self.assertTrue(
            is_group_umo_allowed(
                "tata:GroupMessage:10001",
                is_private_chat=False,
                allowed_umos=allowed,
            )
        )
        self.assertFalse(
            is_group_umo_allowed(
                "tata:GroupMessage:10002",
                is_private_chat=False,
                allowed_umos=allowed,
            )
        )

    def test_empty_allowlist_denies_all_sessions(self):
        self.assertFalse(
            is_group_umo_allowed(
                "tata:GroupMessage:10001",
                is_private_chat=False,
                allowed_umos=frozenset(),
            )
        )

    def test_wildcard_allows_groups_but_not_private_chat(self):
        allowed = normalize_allowed_umos(["*"])
        self.assertTrue(
            is_group_umo_allowed(
                "tata:GroupMessage:10001",
                is_private_chat=False,
                allowed_umos=allowed,
            )
        )
        self.assertFalse(
            is_group_umo_allowed(
                "tata:FriendMessage:123",
                is_private_chat=True,
                allowed_umos=allowed,
            )
        )


if __name__ == "__main__":
    unittest.main()
