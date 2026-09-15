# Recovery log

Source: session transcript `d2b24766-2a78-4174-8123-67fab27201f8.jsonl`, replayed 2026-09-15T16:58:41

```
tool events collected (deduped): 665
[2026-08-22T01:36:56 L2055]
  Heredoc  render_shot.py           3143B
[2026-08-22T01:36:56 L2055]
  Heredoc  shots.json               3809B
[2026-08-22T01:37:32 L2075]
  PyFAIL   shots.json             changed=- ERR AttributeError: module 'urllib' has no attribute 'request'
[2026-08-22T01:38:19 L2102]
  PyFAIL   shots.json             changed=- ERR RuntimeError: sandbox: faster_whisper.__path__ is not available during recovery
[2026-08-22T01:42:25 L2155]
  Write    lipsync_shot.py          3681B
[2026-08-22T01:43:54 L2162]
  Write    assemble.py              9032B
[2026-08-22T01:47:29 L2284]
  Edit     assemble.py            x1 (165B->535B)
[2026-08-22T01:47:39 L2291]
  Edit     assemble.py            x2 (23B->24B)
[2026-08-22T01:47:59 L2305]
  Write    voicecheck.py            2375B
[2026-08-22T01:55:12 L2423]
  PyBlock  assemble.py            changed=['assemble.py'] 
[2026-08-22T02:19:32 L2721]
  PyBlock  shots.json             changed=['shots.json'] 
[2026-08-22T02:21:56 L2741]
  PyBlock  render_shot.py         changed=['render_shot.py'] 
[2026-08-22T02:23:16 L2748]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-render\\voices\\manifest.json'
[2026-08-22T02:23:16 L2748]
  PyFAIL   shots.json             changed=- ERR RuntimeError: sandbox: faster_whisper.__path__ is not available during recovery
[2026-08-22T02:34:16 L2869]
  Edit     lipsync_shot.py        x1 (95B->155B)
[2026-08-22T02:34:56 L2884]
  PyBlock  lipsync_shot.py        changed=- 
[2026-08-22T02:36:14 L2898]
  Write    lipsync_shot.py          5028B
[2026-08-22T02:36:54 L2924]
  Edit     assemble.py            x1 (176B->291B)
[2026-08-22T03:21:34 L3136]
  Write    library_export.py       14695B
[2026-08-22T03:22:06 L3149]
  Write    find_clip.py             2064B
[2026-08-22T03:26:44 L3191]
  Edit     find_clip.py           x1 (165B->212B)
[2026-08-22T03:41:18 L3257]
  PyBlock  shots.json             changed=- 
[2026-08-22T03:42:52 L3283]
  Edit     assemble.py            x1 (729B->1231B)
[2026-08-22T03:43:07 L3290]
  Edit     assemble.py            x1 (553B->1063B)
[2026-08-22T03:43:35 L3297]
  Write    sts_shot.py              4660B
[2026-08-22T03:43:54 L3310]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\scripts.json'
[2026-08-22T03:44:22 L3332]
  PyFAIL   shots.json             changed=- ERR KeyError: 'dental'
[2026-08-22T03:44:39 L3339]
  Edit     assemble.py            x1 (34B->129B)
[2026-08-22T03:47:31 L3380]
  Edit     assemble.py            x1 (570B->815B)
[2026-08-22T03:47:42 L3388]
  Edit     assemble.py            x1 (26B->92B)
[2026-08-22T03:47:50 L3395]
  Edit     assemble.py            x1 (36B->26B)
[2026-08-22T03:49:38 L3437]
  Edit     library_export.py      x1 (105B->747B)
[2026-08-22T03:49:53 L3444]
  Edit     library_export.py      x1 (403B->781B)
[2026-08-22T03:50:02 L3457]
  Edit     library_export.py      x1 (107B->114B)
[2026-08-22T03:50:14 L3464]
  Edit     library_export.py      x1 (407B->736B)
[2026-08-22T03:50:22 L3471]
  Edit     library_export.py      x1 (109B->112B)
[2026-08-22T04:07:28 L3649]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\scripts.json'
[2026-08-22T04:08:10 L3662]
  Heredoc  render_with_wallet.py    5457B
[2026-08-22T04:08:22 L3669]
  Edit     library_export.py      x1 (160B->814B)
[2026-08-22T04:08:31 L3676]
  Edit     library_export.py      x1 (77B->88B)
[2026-08-22T04:08:42 L3689]
  Edit     library_export.py      x1 (137B->276B)
[2026-08-22T04:25:09 L3783]
  PyFAIL   shots.json             changed=- ERR KeyError: 'general'
[2026-08-22T04:28:19 L3850]
  Edit     render_with_wallet.py  x1 (138B->199B)
[2026-08-22T04:51:09 L4004]
  Heredoc  make_look.py             2352B
[2026-08-22T04:52:31 L4052]
  Write    make_avatar.py           2574B
[2026-08-22T04:53:06 L4066]
  MISS     render_shot.py         old_string not found (438B) -> flagged
[2026-08-22T04:53:30 L4084]
  Edit     render_shot.py         x1 (439B->1080B)
[2026-08-22T04:53:45 L4092]
  PyFAIL   shots.json             changed=- ERR KeyError: 'general'
[2026-08-22T04:54:07 L4112]
  Edit     library_export.py      x1 (216B->525B)
[2026-08-22T04:54:20 L4119]
  Edit     library_export.py      x1 (68B->0B)
[2026-08-22T04:54:30 L4126]
  Edit     library_export.py      x1 (109B->180B)
[2026-08-22T04:54:39 L4140]
  Edit     library_export.py      x1 (88B->103B)
[2026-08-22T04:54:48 L4147]
  Edit     library_export.py      x1 (139B->331B)
[2026-08-22T04:55:00 L4154]
  Edit     library_export.py      x1 (106B->701B)
[2026-08-22T04:58:53 L4203]
  PyBlock  looks.json             changed=- 
[2026-08-22T05:02:22 L4279]
  PyBlock  looks.json             changed=- 
[2026-08-22T05:06:54 L4401]
  Edit     library_export.py      x1 (159B->736B)
[2026-08-22T05:25:46 L4468]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\scripts.json'
[2026-08-22T05:26:41 L4501]
  Edit     library_export.py      x1 (125B->558B)
[2026-08-22T05:26:53 L4508]
  Edit     library_export.py      x1 (190B->384B)
[2026-08-22T05:27:05 L4515]
  PyBlock  looks.json             changed=- 
[2026-08-22T05:44:15 L4567]
  Edit     render_shot.py         x1 (254B->408B)
[2026-08-22T05:44:33 L4574]
  PyFAIL   looks.json,shots.json  changed=- ERR KeyError: 'medspa'
[2026-08-22T05:44:58 L4594]
  Edit     library_export.py      x1 (285B->966B)
[2026-08-22T05:45:07 L4601]
  Edit     library_export.py      x1 (70B->128B)
[2026-08-22T05:45:16 L4609]
  Edit     library_export.py      x1 (103B->113B)
[2026-08-22T05:45:27 L4622]
  Edit     library_export.py      x1 (192B->380B)
[2026-08-22T05:55:50 L4764]
  Edit     assemble.py            x1 (13B->974B)
[2026-08-22T05:56:01 L4771]
  Edit     assemble.py            x2 (62B->90B)
[2026-08-22T14:07:01 L4846]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\scripts.json'
[2026-08-22T14:08:28 L4873]
  Edit     render_shot.py         x1 (277B->402B)
[2026-08-22T14:08:52 L4887]
  Edit     library_export.py      x1 (179B->839B)
[2026-08-22T14:09:06 L4901]
  Edit     library_export.py      x1 (128B->198B)
[2026-08-22T14:09:16 L4908]
  Edit     library_export.py      x1 (113B->120B)
[2026-08-22T14:09:27 L4915]
  Edit     library_export.py      x1 (188B->343B)
[2026-08-22T14:09:38 L4928]
  Edit     library_export.py      x1 (193B->409B)
[2026-08-22T14:09:53 L4935]
  Edit     library_export.py      x1 (295B->259B)
[2026-08-22T14:10:07 L4943]
  PyBlock  looks.json             changed=- 
[2026-08-22T14:18:09 L5013]
  Edit     assemble.py            x1 (300B->722B)
[2026-08-22T14:19:38 L5087]
  PyFAIL   shots.json             changed=- ERR KeyError: 'law'
[2026-08-22T14:20:59 L5115]
  PyFAIL   shots.json             changed=- ERR KeyError: 'law'
[2026-08-22T14:26:51 L5175]
  PyFAIL   shots.json             changed=- ERR KeyError: 'law'
[2026-08-22T14:27:50 L5189]
  Edit     library_export.py      x1 (309B->346B)
[2026-08-22T14:47:28 L5507]
  Edit     assemble.py            x1 (104B->966B)
[2026-08-22T14:47:49 L5514]
  Edit     assemble.py            x1 (776B->1182B)
[2026-08-22T14:48:06 L5527]
  Edit     assemble.py            x1 (155B->154B)
[2026-08-22T14:48:46 L5534]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\scripts.json'
[2026-08-22T16:32:05 L5601]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\brand_personas.json'
[2026-08-22T16:32:33 L5614]
  Edit     render_shot.py         x1 (298B->626B)
[2026-08-22T16:33:13 L5628]
  PyFAIL   looks.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'voice_candidates_raw.json'
[2026-08-22T16:33:39 L5641]
  Edit     library_export.py      x1 (60B->1559B)
[2026-08-22T16:33:55 L5648]
  Edit     library_export.py      x1 (120B->143B)
[2026-08-22T16:34:09 L5656]
  Edit     library_export.py      x1 (155B->495B)
[2026-08-22T16:34:28 L5669]
  Edit     library_export.py      x1 (200B->1268B)
[2026-08-22T16:34:40 L5676]
  Edit     library_export.py      x1 (69B->174B)
[2026-08-22T16:34:51 L5683]
  Edit     library_export.py      x1 (164B->185B)
[2026-08-22T16:35:10 L5696]
  Edit     library_export.py      x1 (249B->302B)
[2026-08-22T16:35:26 L5704]
  Edit     library_export.py      x1 (459B->658B)
[2026-08-22T16:35:43 L5711]
  Edit     library_export.py      x1 (353B->486B)
[2026-08-22T16:35:58 L5724]
  Edit     library_export.py      x1 (112B->209B)
[2026-08-22T16:45:05 L5862]
  PyFAIL   shots.json             changed=- ERR KeyError: 'autoadvisor'
[2026-08-22T17:02:49 L6076]
  Edit     assemble.py            x1 (722B->1423B)
[2026-08-23T01:24:50 L6264]
  Heredoc  sync_drift.py            1502B
[2026-08-23T01:30:52 L6278]
  PyFAIL   shots.json             changed=- ERR KeyError: 'autoadvisor'
[2026-08-23T01:32:37 L6301]
  Write    word_audit.py            3468B
[2026-08-23T01:38:53 L6319]
  Write    word_audit.py            4466B
[2026-08-23T01:39:14 L6330]
  PyFAIL   shots.json             changed=- ERR RuntimeError: sandbox: faster_whisper.__path__ is not available during recovery
[2026-08-23T01:45:10 L6340]
  Edit     word_audit.py          x1 (178B->654B)
[2026-08-23T01:45:22 L6345]
  Edit     word_audit.py          x1 (111B->441B)
[2026-08-23T01:45:54 L6356]
  PyFAIL   shots.json             changed=- ERR RuntimeError: sandbox: faster_whisper.__path__ is not available during recovery
[2026-08-23T02:03:37 L6415]
  PyBlock  word_audit.py          changed=['word_audit.py'] 
[2026-08-23T02:03:37 L6415]
  PyBlock  word_audit.py          changed=- 
[2026-08-23T02:16:26 L6473]
  Write    make_thumbs.py           4691B
[2026-08-23T02:18:47 L6502]
  PyBlock  make_thumbs.py         changed=['make_thumbs.py'] 
[2026-08-23T02:31:44 L6591]
  Write    post_plan.py             8029B
[2026-08-23T02:39:53 L6707]
  Write    yt_post.py               3058B
[2026-08-23T17:51:07 L6850]
  Edit     yt_post.py             x1 (111B->371B)
[2026-08-24T13:28:04 L7300]
  PyBlock  make_look.py           changed=['make_look.py'] 
[2026-08-24T18:16:21 L7509]
  PyFAIL   shots.json             changed=- ERR RuntimeError: sandbox: subprocess.run is not available during recovery
[2026-08-24T18:16:41 L7516]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\Content Engine\\.env'
[2026-08-24T18:17:22 L7529]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\Content Engine\\.env'
[2026-08-24T18:19:17 L7536]
  PyFAIL   shots.json             changed=- ERR KeyError: 'salisburyre'
[2026-08-24T18:19:17 L7536]
  PyFAIL   shots.json             changed=- ERR KeyError: 'salisburyre'
[2026-08-24T18:19:56 L7555]
  Edit     assemble.py            x1 (259B->775B)
[2026-08-24T18:20:18 L7567]
  Edit     assemble.py            x1 (49B->431B)
[2026-08-24T18:20:54 L7579]
  PyFAIL   make_thumbs.py         changed=- ERR RuntimeError: sandbox: subprocess.run is not available during recovery
[2026-08-25T00:18:15 L8049]
  PyFAIL   looks.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\looks.json'
[2026-08-25T00:27:34 L8228]
  PyFAIL   assemble.py,shots.json changed=- ERR RuntimeError: sandbox: subprocess.run is not available during recovery
[2026-08-25T00:27:50 L8243]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\Content Engine\\.env'
[2026-08-25T00:30:35 L8259]
  PyFAIL   shots.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\Content Engine\\.env'
[2026-08-25T00:32:47 L8298]
  PyFAIL   shots.json             changed=- ERR RuntimeError: sandbox: lineage.run_id is not available during recovery
[2026-08-26T18:17:12 L9738]
  PyFAIL   shots.json             changed=- ERR KeyError: 'sre-buyer'
[2026-08-26T18:18:13 L9769]
  PyBlock  shots.json             changed=['shots.json'] 
[2026-08-26T18:19:14 L9789]
  Write    make_vo.py               6541B
[2026-08-26T18:20:19 L9808]
  Edit     make_vo.py             x1 (170B->187B)
[2026-08-26T18:23:28 L9820]
  Edit     make_vo.py             x1 (635B->624B)
[2026-08-26T18:23:35 L9832]
  PyFAIL   make_vo.py             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\Content Engine\\.env'
[2026-08-26T18:25:19 L9839]
  PyBlock  shots.json             changed=['shots.json'] 
[2026-08-27T00:40:18 L9999]
  PyFAIL   looks.json,shots.json  changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\looks.json'
[2026-08-27T00:46:05 L10046]
  PyBlock  lipsync_shot.py        changed=['lipsync_shot.py'] 
[2026-08-27T00:57:12 L10107]
  PyFAIL   shots.json             changed=- ERR KeyError: 'sre-seller'
[2026-08-27T00:57:56 L10121]
  Write    reroll_a.py              5904B
[2026-08-27T01:25:51 L10177]
  PyFAIL   looks.json             changed=- ERR FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Cory\\Downloads\\neuron-ad-personas\\looks.json'
[2026-08-27T17:35:49 L10454]
  PyFAIL   assemble.py,shots.json changed=['shots.json'] ERR AssertionError: 
[2026-08-27T17:36:23 L10466]
  Write    intro_run.py             7091B
[2026-08-27T17:58:08 L10573]
  PyFAIL   intro_run.py,shots.json,lipsync_shot.py changed=['shots.json'] ERR FileNotFoundError: [Errno 2] No such file or directory: 'sre-intro\\script.md'
[2026-08-27T18:00:12 L10615]
  PyBlock  make_vo.py             changed=['make_vo.py'] 
[2026-08-27T18:10:19 L10662]
  PyBlock  make_vo.py             changed=- 
[2026-08-27T18:19:19 L10694]
  Write    intro_partial.py         3162B
[2026-08-27T19:48:22 L10860]
  PyFAIL   intro_run.py           changed=- ERR AttributeError: module 'urllib' has no attribute 'request'
[2026-08-27T21:19:33 L10893]
  PyFAIL   render_shot.py,intro_run.py changed=- ERR RuntimeError: sandbox: subprocess.run is not available during recovery
[2026-08-27T21:52:32 L10920]
  PyBlock  render_shot.py,intro_run.py changed=['intro_run.py'] 

== GATES ==
  compile  assemble.py            OK (15975B)
  marker   assemble.py            'script_align' present
  compile  find_clip.py           OK (2145B)
  compile  intro_partial.py       OK (3225B)
  compile  intro_run.py           OK (7670B)
  marker   intro_run.py           'fresh cinematic on disk' present
  compile  library_export.py      OK (25010B)
  compile  lipsync_shot.py        OK (5447B)
  marker   lipsync_shot.py        'clip_sha' present
  marker   lipsync_shot.py        'tpad=stop_mode=clone' MISSING
  ABSENT   looks.json
  compile  make_avatar.py         OK (2610B)
  compile  make_look.py           OK (3013B)
  marker   make_look.py           '--scene=' present
  compile  make_thumbs.py         OK (4710B)
  compile  make_vo.py             OK (8160B)
  marker   make_vo.py             'TTS_MODELS' present
  compile  post_plan.py           OK (8142B)
  compile  render_shot.py         OK (4770B)
  compile  render_with_wallet.py  OK (5584B)
  compile  reroll_a.py            OK (6009B)
  json     shots.json             OK (19366B)
  compile  sts_shot.py            OK (4724B)
  compile  sync_drift.py          OK (1523B)
  compile  voicecheck.py          OK (2411B)
  compile  word_audit.py          OK (6049B)
  compile  yt_post.py             OK (3380B)

events applied: 152; flagged for review: 41; gate failures: 1
  FLAG ('shots.json', 'PyFAIL L2075', "AttributeError: module 'urllib' has no attribute 'request'")
  FLAG ('shots.json', 'PyFAIL L2102', 'RuntimeError: sandbox: faster_whisper.__path__ is not available during recovery')
  FLAG ('shots.json', 'PyFAIL L2748', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-render\\\\voices\\\\manifest.json'")
  FLAG ('shots.json', 'PyFAIL L2748', 'RuntimeError: sandbox: faster_whisper.__path__ is not available during recovery')
  FLAG ('shots.json', 'PyFAIL L3310', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\scripts.json'")
  FLAG ('shots.json', 'PyFAIL L3332', "KeyError: 'dental'")
  FLAG ('shots.json', 'PyFAIL L3649', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\scripts.json'")
  FLAG ('shots.json', 'PyFAIL L3783', "KeyError: 'general'")
  FLAG ('render_shot.py', 'Edit', 'LOOKS = {"P1": "38fe6195513c85f6e11f4a6355f8c2d3",   # Neuron P1 Operator (photo')
  FLAG ('shots.json', 'PyFAIL L4092', "KeyError: 'general'")
  FLAG ('shots.json', 'PyFAIL L4468', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\scripts.json'")
  FLAG ('looks.json,shots.json', 'PyFAIL L4574', "KeyError: 'medspa'")
  FLAG ('shots.json', 'PyFAIL L4846', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\scripts.json'")
  FLAG ('shots.json', 'PyFAIL L5087', "KeyError: 'law'")
  FLAG ('shots.json', 'PyFAIL L5115', "KeyError: 'law'")
  FLAG ('shots.json', 'PyFAIL L5175', "KeyError: 'law'")
  FLAG ('shots.json', 'PyFAIL L5534', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\scripts.json'")
  FLAG ('shots.json', 'PyFAIL L5601', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\brand_personas.json'")
  FLAG ('looks.json', 'PyFAIL L5628', "FileNotFoundError: [Errno 2] No such file or directory: 'voice_candidates_raw.json'")
  FLAG ('shots.json', 'PyFAIL L5862', "KeyError: 'autoadvisor'")
  FLAG ('shots.json', 'PyFAIL L6278', "KeyError: 'autoadvisor'")
  FLAG ('shots.json', 'PyFAIL L6330', 'RuntimeError: sandbox: faster_whisper.__path__ is not available during recovery')
  FLAG ('shots.json', 'PyFAIL L6356', 'RuntimeError: sandbox: faster_whisper.__path__ is not available during recovery')
  FLAG ('shots.json', 'PyFAIL L7509', 'RuntimeError: sandbox: subprocess.run is not available during recovery')
  FLAG ('shots.json', 'PyFAIL L7516', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\Content Engine\\\\.env'")
  FLAG ('shots.json', 'PyFAIL L7529', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\Content Engine\\\\.env'")
  FLAG ('shots.json', 'PyFAIL L7536', "KeyError: 'salisburyre'")
  FLAG ('shots.json', 'PyFAIL L7536', "KeyError: 'salisburyre'")
  FLAG ('make_thumbs.py', 'PyFAIL L7579', 'RuntimeError: sandbox: subprocess.run is not available during recovery')
  FLAG ('looks.json', 'PyFAIL L8049', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\looks.json'")
  FLAG ('assemble.py,shots.json', 'PyFAIL L8228', 'RuntimeError: sandbox: subprocess.run is not available during recovery')
  FLAG ('shots.json', 'PyFAIL L8243', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\Content Engine\\\\.env'")
  FLAG ('shots.json', 'PyFAIL L8259', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\Content Engine\\\\.env'")
  FLAG ('shots.json', 'PyFAIL L8298', 'RuntimeError: sandbox: lineage.run_id is not available during recovery')
  FLAG ('shots.json', 'PyFAIL L9738', "KeyError: 'sre-buyer'")
  FLAG ('make_vo.py', 'PyFAIL L9832', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\Content Engine\\\\.env'")
  FLAG ('looks.json,shots.json', 'PyFAIL L9999', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\looks.json'")
  FLAG ('shots.json', 'PyFAIL L10107', "KeyError: 'sre-seller'")
  FLAG ('looks.json', 'PyFAIL L10177', "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\Users\\\\Cory\\\\Downloads\\\\neuron-ad-personas\\\\looks.json'")
  FLAG ('intro_run.py', 'PyFAIL L10860', "AttributeError: module 'urllib' has no attribute 'request'")
  FLAG ('render_shot.py,intro_run.py', 'PyFAIL L10893', 'RuntimeError: sandbox: subprocess.run is not available during recovery')
```

## Manual finish (2026-09-15, after the automated replay)
Blocks the sandbox could not apply (they died on a missing side file or a stubbed call BEFORE their write) were
re-applied by hand from the transcript (`show_block.py <line>`):
- L10573 -> `lipsync_shot.py` two-way fit (freeze-pad when the VO outruns the clip) + `intro_run.py` fit trigger.
- L8049 / L9999 / L10177 -> `personas/looks.json`: `_canonical_base`, `CORY-neutral-A`, `CORY-neutral-C`
  (the builder blocks had written `looks.json` to the rail root; moved to `personas/`).
- L8228 -> `shots.json` `sre-seller` + `sre-buyer` (rebuilt with the resting-mouth prompt language of the 08-27 reroll).
Not recovered on purpose: the six Neuron persona ads other than `auto`/`contractors`, the `salisburyre` toolkit-reel
entry, and the persona `LOOKS` map edit in `render_shot.py` (raw `--look=<id>` covers every current need).
Brokerage: every visible "KW Westfield" became "Simple Choice Real Estate" (re_compliance law since 2026-09-05).
Keys: the legacy `Content Engine\.env` reads became `secrets_vault.get(...)`.
