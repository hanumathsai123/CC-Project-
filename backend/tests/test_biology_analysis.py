import unittest

from fastapi import HTTPException

from main import analyze_gene_expression


class GeneExpressionAnalysisTests(unittest.TestCase):
    def test_reports_groups_differential_genes_and_baseline_score(self):
        data = (
            "sample_id,TP53,EGFR,BRCA1,diagnosis\n"
            "N01,2.1,1.8,2.5,Normal\n"
            "N02,2.4,1.6,2.3,Normal\n"
            "N03,1.9,2.0,2.7,Normal\n"
            "N04,2.2,1.7,2.4,Normal\n"
            "T01,7.8,8.5,3.1,Tumor\n"
            "T02,8.2,7.9,2.8,Tumor\n"
            "T03,7.6,8.7,3.4,Tumor\n"
            "T04,8.4,8.1,3.0,Tumor\n"
        ).encode()

        report = analyze_gene_expression(data, ",")

        self.assertEqual(report["sample_count"], 8)
        self.assertEqual(report["gene_count"], 3)
        self.assertEqual(report["leave_one_out_accuracy_percent"], 100.0)
        self.assertEqual(report["correct_count"], 8)
        self.assertEqual(report["incorrect_count"], 0)
        self.assertTrue(all(prediction["correct"] for prediction in report["sample_predictions"]))
        self.assertTrue(all(0 <= prediction["score_percent"] <= 100 for prediction in report["sample_predictions"]))
        self.assertEqual(report["top_differential_genes"][0]["gene"], "EGFR")
        self.assertEqual(report["groups"][0]["sample_count"], 4)

    def test_rejects_dataset_without_diagnosis_column(self):
        data = b"sample_id,GENE_A,GENE_B\nS01,1,2\nS02,2,1\nS03,3,2\nS04,4,1\n"

        with self.assertRaises(HTTPException) as error:
            analyze_gene_expression(data, ",")

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn("diagnosis column", error.exception.detail)

    def test_rejects_groups_with_only_one_sample(self):
        data = (
            "sample_id,GENE_A,GENE_B,diagnosis\n"
            "S01,1,2,Normal\nS02,2,1,Normal\nS03,3,2,Tumor\nS04,4,1,Normal\n"
        ).encode()

        with self.assertRaises(HTTPException) as error:
            analyze_gene_expression(data, ",")

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn("at least two", error.exception.detail)


if __name__ == "__main__":
    unittest.main()
