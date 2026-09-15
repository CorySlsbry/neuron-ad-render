#!/usr/bin/env python3
"""post_plan.py - build the posting metadata for the 8 persona ads and drive the GEO flywheel routes.

Cory 2026-08-22: "post them all", with three decisions confirmed:
  1. AI-LABEL EVERYTHING. The platform toggles are NOT settable through these APIs (yt_upload's own
     docs: YouTube's altered-content flag is Studio-only; social_post has no AI field), so every
     caption and description carries an explicit disclosure line and the formal per-platform toggle
     is listed in the needs-Cory handoff.
  2. STAGGER. Enqueue into shorts_queue; cadence.allowance already caps per lane per day/week and
     keeps at-cap items queued for the next 11:00/18:00 flush. That IS the stagger, enforced in code.
  3. TIKTOK STAYS MANUAL for Neuron (his 2026-08-10 standing rule); the lane config's mode:manual
     drops the mp4 + caption into Downloads/assets/tiktok automatically.

Routes: queue/shorts_publish -> Instagram + TikTok + Facebook + LinkedIn (lane-locked tokens).
YouTube is NOT in that path - it goes through each lane's channel-guarded uploader, with the custom
thumbnail that the hard rule requires.

Usage:  python post_plan.py --print
        python post_plan.py --enqueue [--dry-run]
"""
import json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = pathlib.Path(r"C:\Users\Cory\.claude\skills\geo-flywheel\references\engine")

DISCLOSURE = "Made with AI. The presenter in this video is an AI-generated character, not a real person."

ADS = [
 dict(key="general-pro", lane="neuron-hq", mp4="general-pro/general-pro_neuron_ad_v1.mp4",
      title="The best kind of phone call | Neuron HQ",
      hook="Here's the best kind of phone call: someone who already decided it's you.",
      body="Before anyone picks a local business now, they search, they read the reviews, and they ask AI who's worth it. When you're the name that keeps coming up, the call comes in already sold.",
      link="https://neuron-hq.com/free-ai-check", cta="See where you show up today. It's free.",
      tags="local business,AI search,GEO,local SEO,small business marketing"),
 dict(key="auto", lane="neuron-hq", mp4="auto/auto_neuron_ad_v3.mp4",
      title="They already picked your shop | Neuron HQ",
      hook="Your best customer this week already picked your shop. He just hasn't called yet.",
      body="Nobody finds a mechanic by driving around anymore. They search, they read your reviews, and then they ask AI who's actually honest around here.",
      link="https://neuron-hq.com/free-ai-check", cta="See where your shop shows up. It's free.",
      tags="auto repair marketing,auto shop,local SEO,AI search,GEO"),
 dict(key="contractors", lane="neuron-hq", mp4="contractors/contractors_neuron_ad_v2.mp4",
      title="She decided it's you on Wednesday | Neuron HQ",
      hook="The homeowner who calls you Thursday already decided it's you. Wednesday night, from the couch.",
      body="She searched, she read your reviews, and then she asked AI who to trust with a job that size. When you're the name that comes back, she isn't collecting three bids to grind you down.",
      link="https://neuron-hq.com/free-ai-check", cta="See where you show up today. It's free.",
      tags="contractor marketing,home services,local SEO,AI search,GEO"),
 dict(key="dental", lane="neuron-hq", mp4="dental/dental_neuron_ad_v1.mp4",
      title="She chose your practice Sunday night | Neuron HQ",
      hook="The new patient who books you Monday already chose your practice. Sunday night, on her phone.",
      body="She read your reviews, she opened two other practices, and then she asked AI which one to trust. When yours is the one that comes back, that first call changes completely.",
      link="https://neuron-hq.com/free-ai-check", cta="See where your practice shows up. It's free.",
      tags="dental marketing,dental practice,local SEO,AI search,GEO"),
 dict(key="medspa", lane="neuron-hq", mp4="medspa/medspa_neuron_ad_v1.mp4",
      title="She picked you last night | Neuron HQ",
      hook="Picture the new client who books with you tomorrow. She already chose you tonight, scrolling on her couch.",
      body="She looked at your reviews, peeked at two other places, and asked AI who does this well around here. When your name keeps coming back, that first message feels different.",
      link="https://neuron-hq.com/free-ai-check", cta="See how you show up today. It's free.",
      tags="med spa marketing,aesthetics,local SEO,AI search,GEO"),
 dict(key="law", lane="neuron-hq", mp4="law/law_neuron_ad_v1.mp4",
      title="The case already picked your firm | Neuron HQ",
      hook="The case that walks in next week already picked your firm. Days before anyone dialed your number.",
      body="They searched at eleven at night, read what other people went through, and asked AI who handles this well. When your firm is the answer, the consult is a different conversation.",
      link="https://neuron-hq.com/free-ai-check", cta="See where your firm shows up. It's free.",
      tags="law firm marketing,attorney marketing,local SEO,AI search,GEO"),
 dict(key="autoadvisor", lane="auto-advisor", mp4="autoadvisor/autoadvisor_neuron_ad_v2.mp4",
      title="A good Tuesday, when the shop runs itself | Auto Advisor",
      hook="Here's what a good Tuesday looks like when your shop runs itself.",
      body="The phone rang at nine last night and the bay got booked. The part was ordered before anyone noticed it was low. One short briefing told you exactly how the shop did.",
      link="https://autoadvisorpartners.com", cta="Start with a free Service-Drive Audit.",
      tags="auto repair,service drive,shop owner,AI for auto shops"),
 dict(key="tbos", lane="top-builder-ai", mp4="tbos/tbos_neuron_ad_v2.mp4",
      title="Know what every job made | Top Builder OS",
      hook="Picture finishing a job on Friday and knowing, right then, exactly what it made.",
      body="Not in a month. Not after midnight at the kitchen table. The invoice goes out from the driveway instead of Sunday night, and the laptop stays closed after dinner.",
      link="https://topbuilderai.com", cta="Start with the free job-profit report.",
      tags="construction,contractor,job costing,QuickBooks,trades"),
]

def caption(a):
    """Social caption: hook, body, CTA, link, disclosure, tags."""
    tags = " ".join("#" + t.replace(" ", "") for t in a["tags"].split(",")[:5])
    return f"{a['hook']}\n\n{a['body']}\n\n{a['cta']}\n{a['link']}\n\n{DISCLOSURE}\n\n{tags}"

def description(a):
    """YouTube description: same, with the disclosure high where it is visible before the fold."""
    return (f"{a['hook']}\n\n{a['body']}\n\n{a['cta']}\n{a['link']}\n\n"
            f"{DISCLOSURE}\n\n#Shorts {' '.join('#' + t.replace(' ', '') for t in a['tags'].split(',')[:5])}")

def main():
    dry = "--dry-run" in sys.argv
    if "--print" in sys.argv:
        for a in ADS:
            print("=" * 78); print(f"{a['key']}  ->  lane {a['lane']}  |  {a['mp4']}")
            print(f"TITLE: {a['title']}"); print("-" * 78); print(caption(a))
        return 0
    if "--enqueue" in sys.argv:
        results = []
        for a in ADS:
            mp4 = HERE/a["mp4"]
            if not mp4.exists(): print(f"SKIP {a['key']}: missing {mp4}"); continue
            cmd = [sys.executable, str(ENGINE/"shorts_queue.py"), "enqueue", "--lane", a["lane"],
                   "--video", str(mp4), "--text", caption(a), "--link", a["link"]]
            if dry: cmd.append("--dry-run")
            r = subprocess.run(cmd, capture_output=True, text=True)
            tail = [l for l in (r.stdout or "").strip().splitlines() if l.startswith("{")]
            print(f"[{a['key']:12s}] rc={r.returncode} {tail[-1][:220] if tail else (r.stderr or '')[-200:]}")
            results.append((a["key"], r.returncode))
        print(f"\nenqueued {sum(1 for _, rc in results if rc == 0)}/{len(results)}")
        return 0
    print(__doc__); return 0

if __name__ == "__main__":
    sys.exit(main())
