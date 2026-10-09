from contextlib import contextmanager
import datetime as dt
import json
from pathlib import Path
import shutil
import uuid
import unittest
from unittest.mock import patch
import urllib.error
import collect as c

CFG = {"provider":"filtered", "accounts_per_day":4, "per_account_cap_usd":0.02,
       "rolling_31_day_cap_usd":3.0, "max_reels_per_profile":50, "newer_than_days":365}
NOW = dt.datetime(2026, 10, 9, 0, 17, tzinfo=c.UTC)

@contextmanager
def test_directory():
    root = Path(__file__).resolve().parent
    target = root / ("test-temp-" + uuid.uuid4().hex)
    target.mkdir(mode=0o777)
    try:
        yield target
    finally:
        # Verify the generated test directory stays inside the test workspace.
        if target.resolve().parent != root or target.is_symlink():
            raise ValueError("Unsafe cleanup path")
        shutil.rmtree(target)

class BudgetTests(unittest.TestCase):
    def test_rotation_and_repeat_protection(self):
        state={"cursor":0,"reservations":[]}; handles=["a","b","c","d","e","f"]
        first=c.reserve(state,handles,CFG,NOW,"first")
        self.assertEqual(first["accounts"],["a","b","c","d"])
        self.assertIsNone(c.reserve(state,handles,CFG,NOW,"retry"))
        self.assertEqual(c.reserve(state,handles,CFG,NOW+dt.timedelta(days=1),"second")["accounts"],["e","f","a","b"])

    def test_cap_and_expiry_including_failed_runs(self):
        cfg={**CFG,"per_account_cap_usd":0.10,"rolling_31_day_cap_usd":0.30}
        state={"cursor":0,"reservations":[]}
        entry=c.reserve(state,["a","b","c","d"],cfg,NOW,"first")
        self.assertEqual(len(entry["accounts"]),3)
        entry["status"]="partial_or_failed"
        self.assertIsNone(c.reserve(state,["a"],cfg,NOW+dt.timedelta(days=1),"second"))
        self.assertIsNotNone(c.reserve(state,["a"],cfg,NOW+dt.timedelta(days=32),"third"))

    def test_no_billing_calls_without_token_and_paid_plan_is_blocked(self):
        with patch.object(c,"config",return_value=CFG), patch.object(c,"accounts",return_value=["a"]), patch.dict(c.os.environ,{"APIFY_TOKEN":""}):
            with patch.object(c,"api") as api:
                c.prepare("no-token"); api.assert_not_called()
        with patch.object(c,"config",return_value=CFG), patch.object(c,"accounts",return_value=["a"]), patch.dict(c.os.environ,{"APIFY_TOKEN":"test"}), patch.object(c,"api",return_value={"data":{"plan":{"tier":"BRONZE","monthlyBasePriceUsd":19}}}):
            with self.assertRaises(ValueError): c.prepare("paid")

    def test_corrupt_ledger_does_not_reset(self):
        with test_directory() as temp:
            file=Path(temp)/"budget.json";file.write_text("broken",encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError): c.read(file,{"reservations":[]})

    def test_finite_cost_config_only(self):
        with test_directory() as temp, patch.object(c,"ROOT",Path(temp)):
            for bad in [0,True,"NaN",0.50]:
                c.write(Path(temp)/"config.json",{**CFG,"per_account_cap_usd":bad})
                with self.assertRaises(Exception): c.config()

class DataTests(unittest.TestCase):
    def test_view_threshold_and_untrusted_urls(self):
        row={"play_count":10_000_000,"shortcode":"Ab_12","username":"a"}
        self.assertEqual(c.normalize(row,NOW.isoformat(),"filtered")["views"],10_000_000)
        for bad in [9_999_999,True,"10000000",float("nan"),float("inf")]:
            self.assertIsNone(c.normalize({**row,"play_count":bad},NOW.isoformat(),"filtered"))
        self.assertIsNone(c.normalize({"play_count":10_000_000,"url":"https://evil.test/reel/Ab/"},NOW.isoformat(),"filtered"))

    def test_alternative_mapping_preserves_metric(self):
        row={"productType":"clips","shortCode":"Ab","videoPlayCount":11_000_000,"videoViewCount":5,"ownerUsername":"a"}
        mapped=c.normalize(row,NOW.isoformat(),"apify")
        self.assertEqual(mapped["metric"],"videoPlayCount")
        self.assertEqual(mapped["views"],11_000_000)
        self.assertIsNone(c.normalize({**row,"productType":"feed"},NOW.isoformat(),"apify"))

    def test_failure_preserves_old_data_and_partial_success(self):
        with test_directory() as temp, patch.object(c,"ROOT",Path(temp)), patch.dict(c.os.environ,{"APIFY_TOKEN":"test"}):
            state={"cursor":0,"reservations":[]}
            c.reserve(state,["a","b"],CFG,dt.datetime.now(c.UTC),"test")
            c.write(Path(temp)/"data/budget.json",state)
            c.write(Path(temp)/"accounts.json",["a","b"])
            c.write(Path(temp)/"data/reels.json",{"items":[{"id":"old","views":12_000_000,"url":"https://www.instagram.com/reel/old/","username":"a"}]})
            with patch.object(c,"api",side_effect=[[{"shortcode":"new","play_count":15_000_000,"username":"a"}],urllib.error.HTTPError("",429,"",None,None)]) as api:
                with self.assertRaises(RuntimeError):c.collect("test")
                self.assertEqual(api.call_count,2)
                self.assertIn("maxTotalChargeUsd=0.02",api.call_args[0][1])
                self.assertNotIn("maxItems",api.call_args[0][1])
                self.assertEqual(api.call_args[0][2]["usernames"],["b"])
            data=c.read(Path(temp)/"data/reels.json")
            self.assertEqual({x["id"] for x in data["items"]},{"old","new"})
            self.assertEqual(c.read(Path(temp)/"data/status.json")["accounts"][1]["error"],"HTTP 429")
            with patch.object(c,"api") as api:
                c.collect("test"); api.assert_not_called()

if __name__=="__main__":unittest.main()
