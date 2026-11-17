# Other CD rippers and disc tools: what Platterpus lacks, and where it can lead

Research for Platterpus (Qt GUI over a cyanrip fork on libcdio-paranoia). Taken 2026-11-03.
Research only: nothing was changed or posted. Platterpus's own features are taken from the
baseline in the request and were not researched.

**How to read this.** Every fact carries a source key `[Sn]`, listed in section 0 with its URL.
Every source was checked on 2026-11-03. Some pages (Hydrogenaudio wiki, a dBpoweramp forum
thread, the Redump wiki) refused direct fetches; they were read through a search service's
fetch of the same URL, which is noted. Where a fact comes from a forum or a community-maintained
table rather than the vendor, it says so. **UNVERIFIED** marks anything not confirmed by a
source read today.

---

## 0. Sources (all checked 2026-11-03)

| Key | Source | URL |
|---|---|---|
| S1 | Hydrogenaudio wiki, *Comparison of CD rippers* (community table, undated, may lag releases) | https://wiki.hydrogenaudio.org/index.php?title=Comparison_of_CD_rippers |
| S2 | Hydrogenaudio wiki, *AccurateRip* | https://wiki.hydrogenaudio.org/index.php?title=AccurateRip |
| S3 | Hydrogenaudio wiki, *Secure ripping* | https://wiki.hydrogenaudio.org/index.php?title=Secure_ripping |
| S4 | Hydrogenaudio wiki, *EAC Drive Options* | https://wiki.hydrogenaudio.org/index.php?title=EAC_Drive_Options |
| S5 | Hydrogenaudio wiki, *EAC Gap Settings* | https://wiki.hydrogenaudio.org/index.php?title=EAC_Gap_Settings |
| S6 | CUETools wiki, *CUETools Database* | https://cue.tools/wiki/CUETools_Database |
| S7 | CUETools changelog (2.2.6 = 2024-06-28) | https://cue.tools/wiki/CUETools_Changelog |
| S8 | CUETools GitHub releases | https://github.com/gchudov/cuetools.net/releases |
| S9 | CUERipper Options | https://cue.tools/wiki/CUERipper_Options |
| S10 | whipper issue #15, *CTDB as an alternative to AccurateRip* (CTDB author's CRC and offset notes, 2018 to 2022) | https://github.com/whipper-team/whipper/issues/15 |
| S11 | Hydrogenaudio forum, CTDB author on parity design (2010) | https://hydrogenaudio.org/index.php/topic,79882.0.html |
| S12 | ctdb-cli (Linux .NET CTDB client, 2026) | https://github.com/Masterisk-F/ctdb-cli |
| S13 | dBpoweramp secure ripper test page | https://dbpoweramp.com/secure-ripper.htm (mirror: http://www.cd-ripper.com/secure-ripper.htm) |
| S14 | dBpoweramp CD Ripper setup guide | https://doc.dbpoweramp.com/dmc/en/cd-ripper-setup-guide.htm |
| S15 | dBpoweramp CD Ripper product page | https://www.dbpoweramp.com/cd-ripper.htm |
| S16 | dBpoweramp Batch Ripper | https://www.dbpoweramp.com/batch-ripper.htm |
| S17 | dBpoweramp version history | https://versions.dbpoweramp.com/?appid=3 |
| S18 | Neowin, dBpoweramp 2026.09.05 notes | https://www.neowin.net/software/dbpoweramp-music-converter-20260905/ |
| S19 | PerfectTUNES | https://www.dbpoweramp.com/perfecttunes.htm |
| S20 | EAC *What's new* (1.7 on 2024-07-13, 1.8 on 2024-07-14) | https://www.exactaudiocopy.de/whats-new/ |
| S21 | Hydrogenaudio wiki, *EAC release history* (1.8 called the final release) | https://wiki.hydrogenaudio.org/index.php?title=EAC_release_history |
| S22 | WineHQ AppDB, EAC 1.8 | https://appdb.winehq.org/objectManager.php?iId=42275&sClass=version |
| S23 | XLD (English page, latest 20250302) | https://tmkk.undo.jp/xld/index_e.html |
| S24 | whipper README | https://github.com/whipper-team/whipper |
| S25 | whipper CHANGELOG (v0.10.0, 2021-05-17) | https://github.com/whipper-team/whipper/blob/develop/CHANGELOG.md |
| S26 | cyanrip README | https://github.com/cyanreg/cyanrip |
| S27 | cyanrip issues list | https://github.com/cyanreg/cyanrip/issues |
| S28 | riprip README | https://github.com/Blobfolio/riprip |
| S29 | riprip releases | https://github.com/Blobfolio/riprip/releases |
| S30 | Rubyripper README | https://github.com/bleskodev/rubyripper |
| S31 | abcde wiki (2.9.3, 2019-02-05) | https://abcde.einval.com/wiki/ |
| S32 | fre:ac home (1.1.7, 2023-03-05) | https://www.freac.org/ |
| S33 | Hydrogenaudio wiki, *Ripping CDs with foobar2000* | https://wiki.hydrogenaudio.org/index.php?title=Foobar2000%3ARipping_CDs_with_foobar2000 |
| S34 | CDex home (2.24, 2020-08-12) | https://cdex.mu/ |
| S35 | Paranoia home (cdparanoia III 10.2, 2008) | https://www.xiph.org/paranoia/ |
| S36 | libcdio-paranoia releases (10.2+2.0.2) | https://github.com/libcdio/libcdio-paranoia/releases |
| S37 | redumper README | https://github.com/superg/redumper |
| S38 | redumper releases (b770 latest seen) | https://github.com/superg/redumper/releases |
| S39 | Redump forum, *audio offset* (redumper author, 2022) | http://forum.redump.org/topic/45004/audio-offset/ |
| S40 | Redump forum, *Updated guidance for audio CD submissions* (2023-01-28) | http://forum.redump.org/topic/47761/updated-guidance-for-audio-cd-submissions/ |
| S41 | Redump wiki (redump.info), *Audio CD Guide* | https://wiki.redump.info/Audio_CD_Guide |
| S42 | Redump wiki (redump.info), *Redumper* | https://wiki.redump.info/Redumper |
| S43 | Redump wiki, *CD Dumping Guide with Audio Tracks (Old)* | http://wiki.redump.org/index.php?title=CD_Dumping_Guide_with_Audio_Tracks_%28Old%29 |
| S44 | DiscImageCreator README | https://github.com/saramibreak/DiscImageCreator |
| S45 | DiscImageCreator releases (20260101 latest) | https://github.com/saramibreak/DiscImageCreator/releases |
| S46 | IsoBuster help, CD-Text | https://www.isobuster.com/help/cd-text |
| S47 | IsoBuster help, Extraction options | https://www.isobuster.com/help/extraction_options |
| S48 | cdrdao home | https://cdrdao.sourceforge.net/ |
| S49 | cdrdao releases / ChangeLog (1.2.6, 2025-12-05) | https://github.com/cdrdao/cdrdao/releases |
| S50 | cdrdao man page | https://man.archlinux.org/man/cdrdao.1.en |
| S51 | ImgBurn home (2.5.8.0, 2013-06-16) | https://www.imgburn.com/ |
| S52 | QPxTool home (0.8.1, 2020-11-10) | https://qpxtool.sourceforge.io/ |
| S53 | Opti Drive Control FAQ (supported drives) | https://www.optidrivecontrol.com/faq.html |
| S54 | Opti Drive Control manual 1.70 | https://www.optidrivecontrol.com/files/OptiDriveControl.pdf |
| S55 | Gough's Tech Zone, *CD C1/C2 error quality scanning* (2025-08-16) | https://goughlui.com/2025/08/16/notes-cd-c1-c2-error-quality-scanning-modern-vs-older-drives-software/ |
| S56 | Picard docs, *Lookup CD* | https://picard-docs.musicbrainz.org/en/latest/usage/retrieve_lookup_cd.html |
| S57 | MusicBrainz, *How to Add Disc IDs* | https://musicbrainz.org/doc/How_to_Add_Disc_IDs |
| S58 | MusicBrainz, *Disc ID Calculation* | https://musicbrainz.org/doc/Disc_ID_Calculation |
| S59 | beets docs, *Using the Auto-Tagger* | https://docs.beets.io/en/stable/guides/tagger.html |
| S60 | OPS Logchecker | https://github.com/OPSnet/Logchecker |
| S61 | libcdio manual (CD-Text, sub-channels) | https://libcdio.github.io/libcdio.html |
| S62 | libcdio `mmc_read_cd` (C2 and sub-channel parameters; Rust binding doc mirrors the C header) | https://docs.rs/libcdio-sys/latest/libcdio_sys/fn.mmc_read_cd.html |
| S63 | CUETools issue #244, CUERipper submits despite test/copy mismatch (2023) | https://github.com/gchudov/cuetools.net/issues/244 |
| S64 | Hydrogenaudio forum, *Test & Copy, Burst vs Secure* (2010) | https://hydrogenaudio.org/index.php/topic,82489.0.html |
| S65 | Hydrogenaudio forum, *XLD C2 producing AccurateRip inconsistencies* (2015, user report) | https://hydrogenaudio.org/index.php/topic,109618.0.html |
| S66 | Blog, *Burst Mode: Accurate or Awful?* (2024-04-01, one user's tests) | https://uwu.network/~sink/blog/2024/04/burst |
| S67 | Automatic Ripping Machine README | https://github.com/automatic-ripping-machine/automatic-ripping-machine |
| S68 | GitHub topic `cd-ripper` (listing of newer projects) | https://github.com/topics/cd-ripper |
| S69 | Hydrogenaudio wiki, *EAC Lossless Backup* | https://wiki.hydrogenaud.io/?title=EAC_Lossless_Backup |

S1 to S5, S33, S69 were read through the search service's fetch, because the wiki returned 403
to a direct fetch. S41 and S42 are Redump's current wiki at redump.info; the redump.org
`Audio_CD` page returned 404 and 503.

### Tool status at a glance

| Tool | Platform | Latest seen | Source |
|---|---|---|---|
| EAC | Windows (Gold/Platinum under Wine 10/11 in 2026 reports) | 1.8, 2024-07-14; described as the final release | S20, S21, S22 |
| dBpoweramp CD Ripper | Windows, macOS | R2026-09-05 (Neowin); R2025-12-04 on the vendor page | S17, S18 |
| CUETools / CUERipper | Windows (.NET) | 2.2.6, 2024-06-28 | S7, S8 |
| XLD | macOS | 20250302 (2025-03-02) | S23 |
| whipper | Linux | v0.10.0, 2021-05-17; repo updated 2026-02-17 | S25, S68 |
| cyanrip (upstream) | Linux, macOS, Windows | no release visible on the page; issue #157 *Time for a new release?* (2026-08-09) | S26, S27 |
| riprip | Linux (x86-64), macOS | v0.10.1 (21 Oct, year not shown; repo updated 2026-10-21); v0.10.0 replaced libcdio with native SG_IO | S29, S68 |
| Rubyripper | Linux | original 0.6.2; fork in bug-fix mode | S30 |
| abcde | Linux | 2.9.3, 2019-02-05 | S31 |
| fre:ac | Windows, macOS, Linux | 1.1.7, 2023-03-05 | S32 |
| CDex | Windows | 2.24, 2020-08-12 | S34 |
| cdparanoia / libcdio-paranoia | Unix | III 10.2 (2008) / 10.2+2.0.2 (7 May, year not shown: UNVERIFIED) | S35, S36 |
| redumper | Windows, Linux, macOS | b770 (29 Oct, year not shown; presumably 2026: UNVERIFIED) | S38 |
| DiscImageCreator | Windows, Linux, macOS | 20260101 | S45 |
| cdrdao | Unix, now native Windows | 1.2.6, 2025-12-05 | S49 |
| ImgBurn | Windows | 2.5.8.0, 2013-06-16 | S51 |
| IsoBuster | Windows | 5.8 named on the site; date UNVERIFIED | S46 |
| QPxTool | Linux (Qt) | 0.8.1, 2020-11-10 | S52 |
| Opti Drive Control | Windows, paid | manual 1.70; release date UNVERIFIED | S53, S54 |
| riprip, ctdb-cli, ready2rip, ARM | newer projects (2024 to 2026) | see section 1C | S12, S28, S67, S68 |

Nero DiscSpeed (CD-DVD Speed's successor inside Nero) was not reached; its current status is
UNVERIFIED. A 2026 forum post calls ODC the former Nero CD Speed, "being further developed", but
that is a forum claim, not a vendor statement (gearspace thread, found by search, not re-read).

---

## 1. Feature matrices

Legend: **Y** yes, **P** partial or limited, **N** not offered, **?** not verified. A cell's
source is in the last column; S1 is a community table and can lag a release.

### 1A. Audio rippers

Columns: **PP** Platterpus (baseline), **EAC**, **dBp** dBpoweramp, **CUE** CUERipper/CUETools,
**XLD**, **whp** whipper, **cyan** cyanrip upstream, **rrip** riprip, **ruby** Rubyripper,
**abcde**, **fre** fre:ac, **fb2k** foobar2000, **CDex**.

#### Accuracy and verification

| Feature | PP | EAC | dBp | CUE | XLD | whp | cyan | rrip | ruby | abcde | fre | fb2k | CDex | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AccurateRip verify | Y | Y | Y | Y | Y | Y | Y | Y | ? | ? | Y | Y | N | S1, S2, S23, S24, S26, S28, S32 |
| AR across pressings (offset variants) | Y | Y (plugin) | Y | Y | Y | N | Y | ? | ? | ? | N | Y | N/A | S1 |
| AR submission | N | Y | Y | N | N | N | N | N | N | N | N | N | N | S2: only EAC and dBpoweramp submit |
| CTDB verify | Y | Y (plugin) | N | Y | N | N | N | Y | N | N | N | N | N | S1, S6, S10, S28 |
| CTDB submit | N | Y (plugin) | N | Y | N | N | N | N | N | N | N | N | N | S6 |
| CTDB repair | N | N | N | Y (CUETools) | N | N | N | N (hands off to CUETools) | N | N | N | N | N | S6, S28 |
| Test & copy (second full read, CRCs compared) | P (re-read only when AR fails) | Y | Y (passes) | Y | Y ("test before copy") | ? | ? | Y (confirmation passes) | Y (trials) | ? | ? | Y (2 or 4 CRCs per block) | ? | S13, S23, S28, S30, S33, S63 |
| Uses C2 pointers | N | Y (first pass) | Y (all passes) | Y | Y | N | N | Y (required) | N | ? | N | N | ? | S1, S3, S28 |
| Cache defeat | Y | Y (overread, FUA) | Y (overread, FUA) | Y (overread) | Y | Y (overread) | Y (overread) | Y | ? | ? | Y | Y | ? | S1, S3, S14, S23, S28 |
| Multi-pass with database check after each pass; "ultra" passes | N | N | Y | N | N | N | N | Y | N | N | N | N | N | S13, S14, S28 |
| Detects drive interpolation | N | ? | Y | ? | ? | N | N | ? | N | N | N | N | N | S13 |
| Signed or checksummed log | Y (open SHA-256) | Y (closed checksum) | ? | ? | Y (signed, tamper check) | N | N | N | P (MD5 per track, not of the log) | N | N | N (no log file) | N | S23, S30, S33, S60 |

#### Error handling and damaged media

| Feature | PP | EAC | dBp | CUE | XLD | whp | cyan | rrip | ruby | abcde | fre | fb2k | CDex | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Suspicious-position report | ? | Y | Y | Y | Y | ? | Y (paranoia summary) | Y | Y | N | ? | P (console) | ? | S26, S30, S63 |
| Max re-reads setting; early abort on badly damaged disc | ? | Y | Y | ? | ? | ? | ? | Y (passes) | Y | N | ? | Y (128 reads) | ? | S14, S28, S33 |
| Resumable rip, per-sample state kept between runs | N | N | N | N | N | N | N | Y | N | N | N | N | N | S28 |
| Merge reads from several drives | N | N | N | N | N | N | N | Y | N | N | N | N | N | S28 |
| Backward / alternating read order | N | N | N | N | N | N | N | Y | N | N | N | N | N | S28 |
| Read speed control | Y (ladder) | Y | ? | ? | ? | ? | ? | ? | ? | ? | ? | Y | ? | S4, S33 |

#### Disc structure

| Feature | PP | EAC | dBp | CUE | XLD | whp | cyan | rrip | ruby | abcde | fre | fb2k | CDex | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HTOA extraction | N | Y | P (not with per-track + cue) | Y | P (pregap excluded or kept) | Y | Y | Y | ? | ? | Y | Y | ? | S1, S5, S9, S23, S24, S28 |
| Gap (index 00) detection | Y | Y | Y | Y | Y | Y | Y | ? | ? | ? | N | N | Y | S1 |
| Gap handling choices (prev / next / leave out / per-index files) | P (append to previous) | Y | ? | P | P | ? | Y (default, drop, merge, track) | ? | ? | ? | N | N | ? | S5, S26 |
| Index 02+ points | ? | Y (cue scan) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | S1 |
| Data track / Enhanced CD extraction | N | ? | N | N | ? | N | Y (raw 2352-byte .bin) | N | N | N | N | N | N | S26 |
| CD-Text read | ? | Y | Y | N | Y | N | N | Y | ? | Y | Y | Y | Y | S1, S15, S23, S28, S31, S32 |
| ISRC read | Y | Y (cue) | Y | Y (cue) | Y | Y | P (naming key) | Y | ? | ? | P (shown) | ? | ? | S1, S15, S23, S25, S26, S28, S32 |
| MCN / UPC read | ? | Y (cue) | Y | Y (cue) | ? | ? | ? | Y | ? | ? | ? | ? | ? | S1, S15, S29 |
| CD+G (R-W sub-channel) | N | N | N | N | N | N | N | N | N | N | N | N | N | none found; see 1B |
| Pre-emphasis detection source | TOC and sub-channel (FLAGS PRE) | TOC only | Y (per track; bug fixed R2025-11-12) | TOC + subcode | TOC + subcode | TOC only | TOC + subcode | ? | ? | ? | TOC only | ? | ? | S1, S17, S26 |
| De-emphasis filter | Y (optional) | N | Y | ? | ? | N | Y | ? | ? | ? | ? | ? | ? | S17, S26 |
| HDCD decode | Y | N | Y (to 24-bit) | Y (CUETools) | ? | N | N | N | N | N | N | Y (plugin: UNVERIFIED) | N | S14, S15 |
| Copy-protection / TOC manipulation handling | N | ? | ? | ? | ? | N | N | N | N | N | N | N | N | see 1B |
| Lead-in / lead-out overread | ? | Y (option) | Y (option, mostly Plextor) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | S4, S14 |

#### Output

| Feature | PP | EAC | dBp | CUE | XLD | whp | cyan | rrip | ruby | abcde | fre | fb2k | CDex | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Single-file image + cue | N | Y | Y | Y | Y | N | N | N | ? | Y (FLAC + embedded cue) | Y | Y | N | S1, S23, S31 |
| Several cue styles (gaps appended, noncompliant, single file) | P (one cue) | Y | P | Y | Y | P | P | Y (.cue and .toc) | ? | ? | Y | P | P | S1, S7, S28 |
| cdrdao `.toc` output | N | N | N | N | N | N | N | Y | N | N | N | N | N | S29 |
| EAC-layout log | Y | Y | N | Y (option) | N (own layout) | Y (plugin) | N | N | N | N | N | N | N | S9, S24, S27 |
| Encode to several formats in one rip | Y (derived from FLAC) | ? | Y (multi-encoder) | ? | ? | N | ? | N (WAV only) | P (several codecs) | ? | ? | ? | ? | S15, S28, S30 |
| Post-rip lossless self-test | Y (flac --test) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | n/a |

#### Metadata

| Feature | PP | EAC | dBp | CUE | XLD | whp | cyan | rrip | ruby | abcde | fre | fb2k | CDex | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MusicBrainz | Y | Y (plugin) | Y | Y | Y | Y | Y | N (IDs only) | Y | Y | Y | Y (plugin) | ? | S1, S30, S31, S32 |
| Discogs | N | Y (via CTDB plugin) | Y | Y | N | N | N | N | N | N | N | Y (plugin) | N | S1 |
| GD3 / AccurateRip Meta | N | Y (GD3 plugin; AR Meta native since 1.7) | Y | N | N | N | N | N | N | N | N | N | N | S1, S15, S20 |
| Several sources reconciled automatically | N | N | Y (PerfectMeta) | N | N | N | N | N | N | N | N | N | N | S1, S15 |
| Barcode input for lookup | N | N | Y (R2025-02-07) | N | N | N | N | N | N | N | N | N | N | S17 |
| AcoustID fingerprint submission | N | Y (plugin) | ? | N | N | N | N | N | N | N | N | N | N | S20 |
| Disc IDs written for later lookups (CDTOC, AR, CTDB, MB) | ? | ? | Y (CDTOC tag, ACCURATERIPDISCID) | ? | ? | ? | ? | Y | ? | ? | ? | ? | ? | S17, S29 |

#### Workflow

| Feature | PP | EAC | dBp | CUE | XLD | whp | cyan | rrip | ruby | abcde | fre | fb2k | CDex | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Multi-drive batch / autoloaders | N | N | Y (Batch Ripper, robots) | N | N | N | N | N | N | via ARM | N | N | N | S16, S67 |
| Headless / unattended | P (scripted test) | N | Y (Batch Ripper) | ? | P (CLI) | Y | Y | Y | ? | Y | Y (freaccmd) | N | N | S7, S23, S32, S67 |
| Library-wide AR re-verification of existing files | N | N | Y (PerfectTUNES) | Y (CUETools verify) | N | N | N | N | N | N | N | N | N | S19, S6 |

#### CD-R and data discs

| Feature | PP | EAC | dBp | CUE | XLD | whp | cyan | rrip | ruby | abcde | fre | fb2k | CDex | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CD-R detection in log | Y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | n/a |
| Audio CD-R burning | N | Y (bundles cdrdao) | ? | N | Y (Apple framework; HTOA fails on some drives) | N | N | N | N | N | N | Y (needs Nero: old manual) | ? | S22, S23 |
| Write-offset handling when burning | N | Y (combined read/write offset) | ? | N | Y (advice: write offset 0 for AR-verifiable burn) | N | N | N | N | N | N | N | N | S4, S23 |

#### Drive analysis

| Feature | PP | EAC | dBp | CUE | XLD | whp | cyan | rrip | ruby | abcde | fre | fb2k | CDex | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Offset from AR drive list | Y | Y | Y | Y | Y (built-in DB) | Y | Y | Y | Y (manual) | ? | Y | Y | ? | S1, S23, S33 |
| Offset found from an AR-known disc | Y | Y | Y | ? | Y | Y ("quite primitive") | Y | Y | ? | ? | ? | Y | ? | S23, S24, S26, S28 |
| Cache size probe | Y | Y (Detect Read Features) | P (fixed 1 MB flush) | ? | Y (adjustable strength) | N | N | N (manual list) | ? | ? | ? | ? | ? | S4, S14, S23, S28 |
| C2 capability test | N | Y (Examine C2, needs a damaged disc) | Y (Detect C2, scratched disc) | Y (per-model C2 mode fixes) | ? | N | N | ? | N | N | N | N | N | S4, S7, S14 |
| Accurate Stream detection | N | Y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | S4 |
| C1/C2 quality scan | N | N | N | N | N | N | N | N | N | N | N | N | N | see 1B |

### 1B. Imaging, burning, analysis and tagging tools

Columns: **red** redumper, **DIC** DiscImageCreator, **Iso** IsoBuster, **cdr** cdrdao,
**Img** ImgBurn, **QPx** QPxTool, **ODC** Opti Drive Control, **Pic** Picard, **beets**.

| Feature | PP | red | DIC | Iso | cdr | Img | QPx | ODC | Pic | beets | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Audio + data + mixed-mode image | N | Y | Y | Y | Y | Y (read mode) | N | N | N | N | S37, S44, S47, S48, S51 |
| Scrambled-mode CD read | N | Y (.scram, 45,150 sectors reserved before LBA 0) | Y | N | N | N | N | N | N | N | S37, S44 |
| Lead-in capture | N | Y (Plextor, negative LBA) | Y | N | N | N | N | N | N | N | S37, S44 |
| Lead-out capture | ? | Y (MediaTek via cache read) | Y | N | N | N | N | N | N | N | S37, S44 |
| Audio write-offset detection | N | Y ("Perfect Audio Offset") | Y (combined offset) | N | N | N | N | N | N | N | S37, S39, S44 |
| Raw sub-channel (P-W) kept | N | Y (raw, uncorrected) | Y (.sub, readable text) | P (engineering view) | Y (R-W rw/rw_raw) | P | N | N | N | N | S37, S44, S47, S50 |
| CD+G capture | N | Y (in raw sub) | Y (in .sub) | ? | Y (`--read-subchan`) | ? | N | N | N | N | S44, S50 |
| C2 map output | N | Y (per-sample state) | Y (.c2, 1 bit per byte) | N | N | N | Y (scan) | Y (scan) | N | N | S37, S44, S52, S54 |
| Protection analysis | N | Y (LibCrypt, SecuROM patterns) | Y (CDS, Key2Audio, SafeDisc, others) | N | N | N | N | N | N | N | S37, S44 |
| Write-offset-independent disc hash | N | Y ("universal hash" of non-zero span) | N | N | N | N | N | N | N | N | S40, S42 |
| Drive capability probe / firmware flash | N | Y (`drive::test`; flashing can brick) | N | N | N | N | N | N | N | N | S37 |
| CD-Text read | ? | ? | Y | Y | Y | ? | N | N | N | N | S1, S46, S48 |
| CD-Text write (burn) | N | N | N | N | Y | ? | N | N | N | N | S48 |
| DAO audio burn with pregap, ISRC, MCN, flags, index | N | N | N | N | Y | Y (cue/bin) | N | N | N | N | S48, S51 |
| Burn verify against image | N | N | N | N | N | Y | N | N | N | N | S51 |
| Damaged / unfinalized CD-R data recovery | N | N | N | Y | N | N | N | N | N | N | S47 |
| C1/C2 (BLER) scan | N | N | N | N | N | P (via DVDInfoPro) | Y (Linux) | Y (Windows, paid) | N | N | S51, S52, S53, S54 |
| Autoloader support | N | N | N | N | N | Y (Nimbie, Primera, RipBox) | N | N | N | N | S51 |
| MusicBrainz disc ID lookup / submission | Y lookup | N | N | N | P (CDDB) | N | N | N | Y (lookup, attach TOC) | P (tags, fingerprints) | S56, S57, S59 |
| Lookup from a ripper log | N | N | N | N | N | N | N | N | Y (EAC, XLD, whipper logs) | N | S56 |
| Acoustic fingerprint tagging | N | N | N | N | N | N | N | N | Y (AcoustID: UNVERIFIED in today's read) | Y (chroma plugin) | S59 |

### 1C. Newer and lesser-known projects (2023 to 2026)

- **riprip** (Rust, Linux and macOS): an iterative recovery ripper. It notes a bad read and moves
  on, keeps each sample's state between runs (1 to 3 times the disc's size on disk), resumes,
  takes reads from several drives, needs C2, verifies against AccurateRip and CTDB, rips HTOA,
  reads CD-Text and sub-Q, and writes `.cue` or `.toc` [S28]. v0.10.0 replaced libcdio with
  native Linux SG_IO [S29]. The closest open-source peer to Platterpus on correctness.
- **ctdb-cli** (2026, .NET 10 on Linux): CTDB parity calculation, verify, **repair** and
  **submission** from a cue plus WAV or FLAC [S12]. Proof that the LGPL CUETools CTDB code runs on
  Linux today.
- **Automatic Ripping Machine** (MIT): udev-triggered, headless, parallel multi-drive ripping;
  audio CDs go through abcde [S67].
- **ready2rip** (Python, "secure Linux CD ripper with AccurateRip and MusicBrainz", updated
  2026-11-03) and **jack** (Python CLI, updated 2026-10-15) appear in the GitHub topic listing
  [S68]. Neither was examined beyond the listing: their features are UNVERIFIED.
- **EZ CD Audio Converter** (Windows, paid): per S1, it uses C2 to flag errors but does not
  re-read, and does not check AccurateRip.
- **EAC under Wine**: WineHQ reports for EAC 1.8 from Linux Mint, LMDE, openSUSE and Arch in
  2025 and 2026 rate it Gold or Platinum, with the CTDB plugin and AccurateRip submission working
  [S22]. For a Linux user, EAC in Wine is a real competitor to Platterpus.

---

## 2. What Platterpus lacks, ranked

Ranked by effect on correctness first, then by value to a serious user. "Fit" names the Linux
library or approach.

### Correctness

**1. CTDB parity verification and repair.**
- Who has it: CUETools (repair), ctdb-cli on Linux (repair and submit); EAC's plugin and
  CUERipper verify against parity [S6, S12].
- Why it matters: re-reading cannot recover a sector the drive never reads correctly. CTDB's
  recovery record fixes "one continuous damaged area up to 30-40 sectors (about half a second)",
  about 75 sectors on popular discs, or as few as 4 scattered sectors in unlucky places [S6].
  Parity also gives a third verdict besides match and no-match: "contains correctable errors"
  [S6]. Platterpus verifies CTDB CRCs only.
- How it works: Reed-Solomon (65536,65528) on 16-bit words, the disc laid out as a matrix of
  rows 10 sectors wide, 8 parity words per column; about 188 KB per disc [S11].
- Difficulty: medium to high. The client library is LGPL [S6]; port `CUETools.Parity` to C or
  C++, or call ctdb-cli as a subprocess first and port later.
- Fit: good. Pure computation over the FLAC master plus an HTTP fetch; no drive access.

**2. C2 error pointers as added evidence, with error concealment turned off.**
- Who has it: EAC, dBpoweramp, CUERipper, XLD, riprip, DiscImageCreator, redumper [S1, S28, S37,
  S44]. cdparanoia, and so libcdio-paranoia, do not use C2 [S3].
- Why it matters: two reads that agree can share one error. dBpoweramp's test: "Without C2 error
  pointers EAC rips, then re-rips and compares - should an error be duplicated in both reads it
  will pass through undetected", and in its tables EAC without C2 let errors through unreported
  [S13]. C2 must never be the only test (see facts F2).
- Difficulty: medium. Read with `mmc_read_cd(..., c2_error_information, ...)` and clear the
  Digital Audio Play bit so the drive returns data without muting or interpolation [S62]. Needs
  a per-drive C2 trust test and a list of drives whose C2 mode needs a different command
  (CUETools ships such fixes in each release [S7]).
- Fit: libcdio's `mmc_read_cd` or raw SG_IO, beside paranoia rather than inside it.

**3. A stronger rule for discs that neither database knows.**
- Who has it: EAC test & copy; dBpoweramp's complete passes and "ultra" passes (min 6, max 10,
  "finish after 2 clear passes"); foobar2000's paranoid mode (four identical CRCs per block)
  [S13, S33, S64].
- Why it matters: Platterpus re-reads until reads agree. Agreement is precision, not accuracy
  [S64]. On a Matshita drive dBpoweramp found new errors "sometimes ... 6 passes in" [S13].
  dBpoweramp also tries to detect a drive's interpolation [S13].
- Difficulty: low to medium. Configurable N-of-M agreement, each pass after a cache flush and
  optionally at another speed, plus C2 (item 2). Log which rule passed each track.
- Fit: existing paranoia loop plus scheduling.

**4. Resumable, per-sample recovery across runs and drives.**
- Who has it: riprip; redumper records per-sample state for "refinement across drives" [S28,
  S37].
- Why it matters: on a damaged disc the best samples come from different reads, different
  sessions and different drives. Paranoia keeps nothing between runs. riprip says it "will rescue
  more data than traditional CD-ripping software, more accurately, and in significantly less
  time" (its own claim) [S28].
- Difficulty: medium to high. A per-sample store of observed values, counts and C2 flags; a
  re-run reads only unconfirmed regions; a merge picks the value with the most agreeing
  confirmations; AR/CTDB confirmation closes a track.
- Fit: SG_IO or libcdio reads; a sidecar file next to the rip.

**5. HTOA extraction, with its own verification.**
- Who has it: EAC, CUERipper ("Preserve HTOA" as track 00), whipper, riprip, foobar2000, fre:ac;
  dBpoweramp only partly [S1, S5, S9, S24, S28].
- Why it matters: hidden audio in track 1's index 00 is lost in a per-track rip [S5]. Neither
  database verifies it: CTDB says "No verification or recovery of HTOA" [S6], and AR's CRC starts
  at track 1 [S2]. So HTOA needs secure-read agreement (and C2) on its own, and the log must say
  so.
- Difficulty: low. cyanrip's pregap modes include `track` [S26]; check whether upstream already
  writes track 1's pregap as a track 00 file.
- Fit: same read path.

**6. Lead-in and lead-out: what the drive can overread, and what lies past the edges.**
- Who has it: EAC and dBpoweramp offer overread (dBpoweramp: "generally only Plextor drives");
  redumper captures lead-in on Plextor and lead-out on many MediaTek drives [S4, S14, S37].
- Why it matters: with an offset, the first or last samples must come from lead-in or lead-out.
  Drives that cannot overread lose those samples, and padding with silence is the accepted fix
  [S2]. Neither database checks the edges (AR skips 2939 and 2940 samples, CTDB 10 sectors at the
  start and 10 to 19.999 at the end) [S2, S10]. Some discs carry real audio past the lead-out
  [S41, S42], which Redump keeps as extra tracks.
- Difficulty: medium. Probe overread per drive, record it in the drive profile, and log for each
  disc whether edge samples were read or padded, and whether the padded range was non-zero on a
  drive that could see it.
- Fit: libcdio reads past the lead-out may fail on most drives; redumper's per-chipset methods are
  the reference.

**7. Check structure against the sub-channel, not only the TOC.**
- Who has it: CUERipper, cyanrip and XLD read pre-emphasis from TOC and subcode; EAC scans the
  subcode for index 02+ when writing a cue; DiscImageCreator and redumper handle protected discs
  [S1, S37, S44].
- Why it matters: "There are several CDs with pre-emphasis which only include the flag in the
  subcode, and not the TOC", and a TOC "is sometimes deliberately incorrect or unreadable on some
  drives, as a copy-protection measure" [S1].
- Difficulty: medium. Cross-check TOC track starts against sub-channel Q index 01 positions, and
  warn on any mismatch; record indexes above 01.
- Fit: libcdio sub-channel reads; formatted Q via `mmc_read_cd` sub-channel selection 2 [S62].

**8. Data tracks and Enhanced CDs.**
- Who has it: cyanrip upstream ("Data track ripping" to raw 2352-byte `.bin`), redumper,
  DiscImageCreator, IsoBuster, cdrdao [S26, S37, S44, S47, S48].
- Why it matters: the disc's data session is part of the release. It also changes disc IDs: a
  MusicBrainz ID ends the audio at the data track's start minus 11,400 sectors [S58]. A known
  upstream bug: ripping "hangs at the end of the last audio track on an Enhanced CD when a
  positive drive offset is set" (cyanrip issue #168, opened 2026-10-18) [S27].
- Difficulty: low (take the upstream code), plus the hang fix.
- Fit: already in the fork's base.

### Completeness and user value

**9. Single-file disc image with a full cue (and a cdrdao `.toc`).** EAC, dBpoweramp, CUERipper,
XLD, foobar2000, fre:ac write image + cue; riprip writes `.cue` or `.toc` [S1, S28]. Users who
reburn or archive want it, and CTDB works on whole discs [S6]. A full cue carries index 00 and
02+, ISRC, CATALOG, FLAGS, CD-Text and HTOA. Low to medium. Fit: the FLAC master already holds
the samples; this is an output writer.

**10. Submission to CTDB, and to MusicBrainz (disc ID, ISRCs).** CTDB submission: EAC's plugin,
CUERipper, CUETools [S6]. AccurateRip submission is closed: "Only two programs submit to AR, EAC
and dBpoweramp ... through the standard AccurateRip access dll" [S2], so it is not reachable.
CTDB submission needs the same parity code as item 1, plus a quality gate (EAC's plugin answers
"Submit result: insufficient quality" when test and copy CRCs differ; CUERipper has submitted
anyway [S63]). MusicBrainz: Picard attaches a disc TOC to a release; libdiscid tools submit ISRCs
[S56, S57]. MusicBrainz asks: "Please do not add DiscIDs from homeburnt CDs" [S57], so gate on
Platterpus's CD-R detection. Medium.

**11. CD-Text and MCN reading, written to cue and tags.** EAC, dBpoweramp, XLD, abcde, fre:ac,
riprip, cdrdao, IsoBuster read CD-Text [S1, S29, S46, S48]. Useful when MusicBrainz has no entry.
Low. Fit: `cdio_get_cdtext` reads and caches it on first call [S61].

**12. CD+G (R-W sub-channel) capture.** cdrdao (`--read-subchan rw` or `rw_raw`),
DiscImageCreator `.sub`, redumper raw sub-channel [S37, S44, S50]. Karaoke discs lose their
graphics without it. Medium; drive support varies ("Not all drives support reading the RW
subcodes from the program area" [S61]). Fit: `mmc_read_cd` sub-channel selection 4 (corrected
R-W) or 1 (raw P-W) [S62].

**13. Multi-drive batch and autoloaders.** dBpoweramp Batch Ripper ("most robots supported",
"over 120 discs per hour ... (6x drives)"), ARM, ImgBurn's autoloader support [S16, S51, S67].
Medium. Fit: udev events, one worker per drive, a queue in the GUI.

**14. Drive and disc quality.** EAC and dBpoweramp test C2 with a deliberately scratched disc
[S4, S14]; QPxTool (Linux, Qt) and ODC scan C1/C2 and BLER on Plextor, BenQ and MediaTek-based
Lite-On drives [S52, S53, S54]. Medium. Fit: QPxTool's libraries are native Linux; integrate or
shell out, on supported drives only. Caveat in F12.

**15. Library re-verification.** PerfectTUNES "AccurateRip verifies previously ripped discs" and
CUETools verifies against both databases [S6, S19]. Platterpus already has the matching code, so
"verify my FLAC library" (from a CDTOC tag or the cue) is low effort.

**16. Metadata breadth.** Discogs, barcode entry, several sources reconciled (PerfectMeta),
AcoustID [S1, S15, S17, S20]. Low to medium each. Also make Platterpus's EAC-layout log parse in
Picard's "Lookup CD from ripper log" [S56] and in OPS Logchecker [S60].

**17. Audio CD-R burning.** cdrdao 1.2.6 (2025-12-05) writes DAO with pregaps, ISRC, MCN, flags,
index marks and CD-Text [S48, S49]; EAC uses a combined read/write offset [S4]. Lowest priority
for a ripper. Fit: drive cdrdao from a generated `.toc`.

---

## 3. Where Platterpus could do better than all of them

1. **One evidence ledger per track.** No tool joins every signal. Record per track (and per
   sample range): AR v1/v2 match and confidence, the pressing offset used, CTDB track CRC, CTDB
   parity verdict (match, correctable, unknown), re-read agreement count, C2 state, which drive
   and pass supplied each region, and which samples no database covers (HTOA, edge frames). Show
   the verdict in the GUI with its reason.

2. **Parity-guided re-reading.** Use the CTDB recovery record to locate damaged columns and
   rows, then re-read only those sectors, then repair what remains, then verify again. The
   pieces exist (riprip's targeted re-reads [S28], CUETools repair [S6]); joining them in one
   loop is new. Whether syndromes localize well enough for this is UNVERIFIED and needs a
   prototype.

3. **Open, checkable logs.** EAC's and XLD's log checksums are closed, so log checkers must call
   out to separate tools [S60]. Platterpus's open SHA-256 can go further: publish the algorithm
   and a verifier, add a JSON log beside the EAC-layout one, optionally signed (minisign or
   ed25519), and test that the EAC-layout log passes Picard's log lookup and OPS Logchecker.

4. **A drive profile built from evidence.** Offset (AR), cache size (probe), overread ability,
   Accurate Stream, and C2 trust learned over time: count every time C2 said clean but the AR or
   CTDB result disagreed. EAC's own docs say its C2 tests cannot show whether all errors are
   reported [S4]; real outcomes can.

5. **A write-offset-independent disc hash.** Log redumper's "universal hash" (SHA-1 of the
   non-zero sample span), which matches the same audio across write offsets [S40, S42]. Users
   can then match a rip to Redump's audio CD entries, and a later rip of another pressing.

6. **Honest edges and HTOA.** Say in the log which samples were overread, which were padded, and
   which no database verified; verify HTOA by agreement and C2 because nothing else can.

7. **Consensus across drives.** Rip once on each of two drives and merge per sample; flag any
   sample on which drives disagree. Only riprip and redumper keep per-sample state [S28, S37];
   neither presents it in a GUI.

8. **A disc health report.** Even without a C1/C2-capable drive, the re-read and C2 map from the
   rip is a heat map of the disc. For CD-Rs, flag rising error counts and suggest a backup now.

9. **CD-R awareness throughout.** Platterpus already detects CD-Rs. Use that to warn about
   2-second TAO gaps [S5], to block MusicBrainz disc ID submission [S57], and to mark the rip as
   a copy in the log.

10. **Linux-native CTDB end to end.** No Linux GUI ripper repairs or submits CTDB today (whipper
    issue #15 has been open since 2015 [S10]; riprip hands repair to CUETools [S28]). Shipping
    it would be a first.

---

## 4. Facts that matter for correctness, and are often got wrong

**F1. Drive caches defeat re-reads.** "When the drive is told to re-read something, it might
just send the cached data instead of actually re-reading the disc." The usual cure reads extra
data to flush the cache; FUA is more efficient "but doesn't have wide hardware support", and of
the rippers listed only EAC and dBpoweramp use it [S3]. EAC never requests less than 64 KB, so a
cache under 64 KB needs no flushing [S4]. dBpoweramp flushes with "a 1024KB cache" by default,
larger than any audio cache it knows [S14]. riprip keeps a hand-maintained cache-size list [S28].

**F2. C2 is unreliable, and must not be the only test.** "Not all drives adhere to the same
standard ... errors can go undetected." EAC's two C2 tests cannot tell "whether all
uncorrectable errors are reported" [S4]. dBpoweramp: "no matter how good a C2 implementation
is on any drive, errors can still sneak through" [S13]. With C2 trusted, a block with no C2 flag
is not re-read, which is "essentially the same as burst mode" [S1]. A 2015 user report shows C2
on a Matshita laptop drive causing AR mismatches that burst mode did not (single report) [S65].
For quality scans, a 2025 test of several drives found MediaTek drives' C1 values "too
optimistic" while C2 counts "seemed more consistent across drives" [S55].

**F3. Two agreeing reads can both be wrong.** "Should an error be duplicated in both reads it
will pass through undetected" [S13]. "T&C is nothing more than a demonstration of precision. It
does not provide any guarantee of accuracy" [S64]. Only a database match from someone else's
disc is strong evidence [S64].

**F4. What AccurateRip does and does not check.**
- Only EAC and dBpoweramp submit, through Illustrate's DLL; other tools read only [S2].
- The checksum skips the first 2939 samples of the first track and the last 2940 samples of the
  last track [S2].
- Gaps must be appended to the previous track (index 00 belongs to the track before it in the
  file) or checksums will not match [S2].
- The v1 checksum leaves about 3% of the audio out (half the right-channel samples in each
  65,536-sample cycle are partly ignored); v2 fixed this and is stored as a separate pressing
  [S2].
- The reference offsets were challenged in 2006 as 30 samples off; the database kept them, and
  since every submission uses the same reference, matching is unaffected [S2]. A ripper must use
  AR's numbers, not a "true" offset.
- A drive that cannot overread loses edge samples; padding them with silence is the accepted
  fix [S2].

**F5. Pressings.** A pressing is the same audio at a different offset [S2]. CTDB "doesn't care":
"Different pressings of the same CD are treated as the same disc" [S6]. **Sources conflict on
AccurateRip v2:** the Hydrogenaudio wiki says v2 "incorporate[d] cross-checking against alternate
pressings" [S2], while CTDB's author wrote in 2021 that accounting for pressing offsets is
"something that AccurateRip V2 doesn't support" [S10]. Read together: the AR database does not
merge pressings; rippers that check offset variants (CUETools, Platterpus) do the cross-check
themselves. That reading is an inference, not a sourced fact.

**F6. What CTDB covers.** Whole discs only; "No verification or recovery of HTOA"; the first 10
frames of track 1 and last 10 frames of the last track are not verified [S6]. The disc CRC
excludes the pregap, the first 10 sectors, and the last 10 to 19.999 sectors, so the covered
length is a multiple of 10 sectors; track CRCs for middle tracks cover the whole track [S10].
Repair limits are in item 1 of section 2.

**F7. HTOA is index 00 of track 1.** A per-track rip "normally omits this audio since there's no
previous track to append it to"; EAC shows track 1 in red when the gap is long enough to hold
HTOA [S5]. Neither database verifies it [S2, S6].

**F8. Pre-emphasis can be in the subcode only.** "A conventional hardware CD player will enable
its de-emphasis circuit based on the subcode, not the TOC", and some discs flag it only there
[S1]. Mixed discs are a trap: dBpoweramp fixed de-emphasis "not being enabled on per-track basis,
if disc being ripped contains tracks with and without pre-emphasis" in R2025-11-12 [S17].

**F9. Enhanced CDs and disc IDs.** MusicBrainz leaves data tracks out of the disc ID and sets
the audio lead-out to the data track's start minus 11,400 sectors (11,250 lead-out/lead-in +
150 pregap) [S58]. CTDB stores the data track's length separately and does not need it to verify
[S6].

**F10. Redump's view of audio offsets.**
- Redump used to dump audio CDs at write offset 0, because "there is no reliable reference point
  in the audio stream (in contrary to a data track)" [S39]. That lost shifted audio in the pregap
  and lead-out, and sometimes split tracks mid-sound [S39].
- redumper's rule (2022-12): pick the one write offset that lines up digital silence with the
  TOC's index 00 ranges; else shift non-zero lead-out or lead-in data back in if it fits; else
  use 0 [S39]. Leftover non-zero lead-in or lead-out data is kept as separate tracks [S40, S42].
- Redump adopted redumper for audio CDs in 2023 because the old method failed "to capture data in
  the lead-in and lead-out" and treated discs with different write offsets as alternates [S40].
- An out-of-spec offset beyond +21065 can make the default split audibly wrong; staff may then
  accept `--force-offset=0` [S41].
- Older Redump guidance: the value used to rip is the combined read+write offset; the write
  offset alone is that minus the drive's AR read offset [S43].
- Consequence for Platterpus: AccurateRip-style rips correct the read offset only. They are right
  for AR and CTDB, and can differ from a Redump dump of the same disc by the disc's write offset.

**F11. Overread can itself cause errors on some drives.** One user found that "disabling
overreading into Lead-In and Lead-Out entirely fixed" suspicious positions on a disc's last
track (one user's tests, 2024) [S66]. Make overread a per-drive setting found by probing.

**F12. Concealment.** In READ CD, when the Digital Audio Play bit is false, audio "should not be
modified by flaw obscuring mechanisms such as audio data mute and interpolate" [S62]. A ripper
that leaves concealment on can be handed plausible, wrong samples. dBpoweramp states that "many
drives" interpolate on error and tries to detect it [S13].

**F13. CD-Rs.** Track-at-once CD-Rs carry 2-second gaps that users may want to remove [S5];
cdrdao's `--tao-source` assumes "150 blocks plus the number of link blocks (usually 2)" [S50].
Do not submit home-burnt disc IDs to MusicBrainz [S57].

**F14. Submission quality.** EAC's CTDB plugin refuses a submission when test and copy CRCs
differ; CUERipper has submitted such rips, because its rip quality counts only suspicious
positions [S63]. A Platterpus submitter should gate on its own agreement and AR evidence.

**F15. libcdio-paranoia version.** 10.2+2.0.2 fixed "a 6-year-old bug, seen primarily by
Whipper users, concerning adjusting of CD-drives that have large sample offsets, or negative
offsets" [S36]. The fork should require at least that release; the year of the release is
UNVERIFIED from the page.

**F16. Accurate Stream.** Nearly all current drives have it; without it, reads can shift
between requests (jitter), and EAC overlaps every read to correct it. EAC turns cache flushing
on automatically when Accurate Stream is off [S4].

---

## 5. Gaps in this research

- dBpoweramp's current CTDB support was not confirmed from the vendor; S1 says "No" and no
  vendor page or changelog read today mentions CTDB. Its batch ripper's secure-ripping behaviour
  is not stated on its page [S16].
- XLD's CTDB support: not on XLD's page [S23]; S1 says "No".
- whipper's exact test & copy behaviour, cyanrip's HTOA output, IsoBuster's audio features
  (beyond CD-Text and raw extraction), Nero DiscSpeed's status, and the dates of several releases
  (libcdio-paranoia 10.2+2.0.2, redumper b770, riprip v0.10.1, IsoBuster 5.8, ODC) are marked
  UNVERIFIED where they appear.
- foobar2000's HDCD and Picard's AcoustID cells are UNVERIFIED.
