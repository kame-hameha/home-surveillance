import vlc
i = vlc.Instance('--verbose 2'.split())
p = i.media_player_new()
p.set_mrl('rtp://@http://192.168.178.142:8000/index.html')
p.play()
