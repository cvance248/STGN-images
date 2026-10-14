# STGN-images

Pictures and posting log for the Scan The Good News Instagram account, @scanthegoodnews. Each post is a King James Bible verse set on a scenic background, with a caption that applies the verse.

- `posts/` holds the picture for every post, named `<date>-<verse>.jpg`. Metricool reads the pictures from here.
- `01-` to `05-*.jpg` are the first five pictures, made by hand before the weekly run existed. Every later picture goes in `posts/`.
- `data/posts-log.json` lists every post: date, verse, look, caption and status.
- `data/settings.json` holds the controls for the weekly run. Set `"paused": true` to stop it. Set `"mode": "draft"` to review each post in Metricool before it goes out.
- `data/verse-bank.json` is the list of verses the run draws from.
- `data/run-log.md` has a short note from each weekly run.
- `tools/` has the scripts the weekly run uses. Their checksums are pinned in the scheduled task, so the run refuses to start if one of them is changed. To change a script, ask Claude to do it, because the pinned checksums have to be updated in the scheduled task at the same time.

Only the repository owner, and the Claude GitHub app installed on this repository, can push changes here. The repository is public because Metricool has to download each picture from a public address, so the log, and with it the captions of upcoming posts, can be read here before they go out.
