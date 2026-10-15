import unittest
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile
from xml.etree import ElementTree
from apps.selfservice.claim_engine import normalize, build_draft, to_docx, InvalidClaim
from apps.selfservice.ai import optional_rewrite, AIUnavailable


def sample():
    return dict(creditor="Демо", debtor="Тест", contract_number="ДЕМО-24", contract_date="2026-09-01", due_date="2026-10-01", amount="640 000,00", description="Синтетические работы", facts_confirmed=True, synthetic_data=True)


class EngineTests(unittest.TestCase):
    def test_amount_normalized(self):
        self.assertEqual(normalize(sample())["amount"], "640000.00")
    def test_invalid_amounts(self):
        for value in ["NaN", "Infinity", "-1", "0", "1.001", "1e99999", "1000000000001", "abc"]:
            with self.subTest(value=value), self.assertRaises(InvalidClaim):
                normalize(dict(sample(), amount=value))
    def test_invalid_dates(self):
        for value in ["2026-02-30", "yesterday", ""]:
            with self.subTest(value=value), self.assertRaises(InvalidClaim):
                normalize(dict(sample(), due_date=value))
    def test_required(self):
        for field in ["creditor", "debtor", "contract_number", "description"]:
            with self.subTest(field=field), self.assertRaises(InvalidClaim):
                normalize(dict(sample(), **{field:""}))
    def test_confirmations(self):
        for field in ["facts_confirmed", "synthetic_data"]:
            for value in [False, "true", 1, None]:
                with self.subTest(field=field, value=value), self.assertRaises(InvalidClaim):
                    normalize(dict(sample(), **{field:value}))
    def test_control_characters(self):
        with self.assertRaises(InvalidClaim): normalize(dict(sample(), description="x\x01"))
    def test_lengths(self):
        for field,limit in [("creditor",200),("description",4000)]:
            with self.subTest(field=field), self.assertRaises(InvalidClaim): normalize(dict(sample(), **{field:"x"*(limit+1)}))
    def test_unreviewed(self):
        text=build_draft(sample())
        self.assertIn("НЕ ПОДПИСАНО И НЕ ОТПРАВЛЕНО",text)
        self.assertIn("640000.00",text)
        self.assertNotIn("ст. 395",text)
    def test_deterministic(self): self.assertEqual(build_draft(sample()),build_draft(sample()))
    def test_docx_xml(self):
        content=to_docx("Текст <script> & тест")
        with ZipFile(BytesIO(content)) as z:
            self.assertEqual(len(z.namelist()),3)
            for name in z.namelist(): ElementTree.fromstring(z.read(name))
            self.assertIn(b"&lt;script&gt;",z.read("word/document.xml"))
            self.assertNotIn(b"TargetMode",z.read("_rels/.rels"))
    def test_network_off(self):
        with patch("apps.selfservice.ai.urlopen",side_effect=AssertionError("network")) as network:
            with self.assertRaises(AIUnavailable): optional_rewrite(sample())
            network.assert_not_called()
    def test_real_data_refused(self):
        with patch("apps.selfservice.ai.urlopen") as network:
            with self.assertRaises(AIUnavailable): optional_rewrite(dict(sample(),synthetic_data=False),enabled=True,provider="zen",model="test",key_file="unused")
            network.assert_not_called()
    def test_missing_model(self):
        with patch("apps.selfservice.ai.urlopen") as network:
            with self.assertRaises(AIUnavailable): optional_rewrite(sample(),enabled=True,provider="zen")
            network.assert_not_called()
    def test_missing_secret(self):
        with patch("apps.selfservice.ai.urlopen") as network:
            with self.assertRaises(AIUnavailable): optional_rewrite(sample(),enabled=True,provider="zen",model="test",key_file="/no/such/secret")
            network.assert_not_called()

if __name__=="__main__": unittest.main()
