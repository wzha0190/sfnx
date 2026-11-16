# Three V100s on one socket

What the exchanges between the cards measured on a one-socket box, against the two-socket box the engine was tuned on
(GPU 0 there on the other socket from 1 and 2). Measured 2026-11-17 at `980873394a53` plus this branch's `FNX_RING3`.

## The box

Tyan S8030 (NPS1), one EPYC 7443, 256 GiB DDR4-2400, three Tesla V100-PCIE-32GB, each PCIe Gen3 x16 to the CPU's root
complex (`nvidia-smi topo -m`: NODE between every pair), 250 W limit, driver 580.178.04, CUDA 12.9. Model: Huihui
Qwen3.8-Flash-Next abliterated v2, Unsloth `UD-Q4_K_XL-V2` recipe, run with prod's settings (`FNX_NGRAM=ram`,
`FNX_MTP_EXPERTS=q4_0`, `FNX_PF_ROWS=4096`). Lab numbers are `tools/lab.sh decode` and `read` on the held model; the
default and `FNX_RING3=1` ran twice each and their passes agreed within 0.5%, the direct exchanges once.

## The links

- Kernel stores between the cards (the engine's start-up probe): 9.7–10.0 GB/s for every directed pair, against the
  two-socket box's 5.4–7.7.
- The ring's pattern, every card storing into the next (`tools/p2p_store_bench BYTES 40 8`): 2.66 GB/s a card at
  41 KB (a 6-row hop), 5.50 at 124 KB, 8.48 at 393 KB, 9.87 at 1 MB. Decode's hops are mostly latency.
- One card storing into both others at once (`tools/p2p_two`): 102 KB to each took 62 us one after the other and
  115.5 us alternating word by word, 130 us with the blocks split between them.
- Copy engines (`tools/p2p_pairs_bench`): one way round the ring 12.3 GB/s a copy at 4 MB, both ways at once 6.2: each
  card's link is full one way, so a two-way prompt ring gains nothing here either.

## Decode's sums and attention partials

Prod's decode, lab (ms a round; edit1 and code1 greedy, prose2 sampled, seeds 1–5):

| Exchange | edit1 | code1 | prose2 | Logits |
| --- | ---: | ---: | ---: | --- |
| The ring, two fp16 values a word (default) | 28.08 | 18.21 | 15.02 | base |
| `FNX_RING3=1`: the ring, three values a word | 27.85 | 18.58 | 15.22 | byte for byte |
| Sums stored straight to each chunk's card and from it to every card (two waits, not four) | 38.46 | 22.23 | 16.86 | differ (rounded once a part) |
| Attention partials stored straight into the heads' card (one hop, not two) | 30.74 | 18.88 | 15.46 | byte for byte |

Batched windows (`tools/lab.sh batch`) with `FNX_RING3=1` were 1–2% slower at 1, 2, 3 and 6 lanes (6 lanes: 18.60
against 18.28 ms a window, with drafts 31.42 against 31.00). The two direct exchanges were tried and taken out; their
numbers are in `src/kernels.cu`'s comment on `k_ring3f`. A card's stores to two peers at once cost more than the
ring's extra hops on this root complex too, not only across sockets. In a CUPTI trace of one edit1 request (its
prompt read and its decode), `k_ring` took 7% of card 0's kernel time and 10% of card 2's, waiting for the slower cards
included: the most any exchange could give back.

## Other settings tried

| Setting | Result |
| --- | --- |
| Clocks locked at 1,380 MHz (`nvidia-smi -lgc`) | the same: 28.11, 18.19, 15.03 ms a round. Boost already held ~1,358 MHz average, decode draws ~120 W a card |
| `FNX_PF_RING_SM=1` | prompt reads 12–27% slower (4k 2,872, 16k 2,936, 30k 2,905 tok/s against 3,249–3,258, 4,030–4,032, 3,966–3,972) |
| `FNX_PF_ATT_PIECES=2` / `8` | 0.3–1.6% slower |
| `FNX_PF_PASS=2` | the same as 4 (3,256, 4,038, 3,955 tok/s) |
| `FNX_PF_PASS=8` | 0.4–1.5% slower, and 407 more experts to RAM for VRAM |

## Drafts and batching

Lab decode at prod's settings (tok/s; edit1, code1, prose2):

| Setting | Result |
| --- | --- |
| `--spec` 6 (prod), `--lookup` 15 (prod) | 397.1, 184.6, 142.4 |
| `--spec` 4 / 8 / 10 / 12 | within 2%: 389.9–397.7, 184.6–187.8, 142.4–142.7. Prose stays at 2.14 tokens a round: acceptance limits it, not the chain's length |
| `--lookup` 8 / 12 | edit1 359.4 / 376.7, the rest the same |
| `FNX_DRAFT_SAMPLE=0` / `FNX_DRAFT_PEN=0` | prose2 137.0 / 140.8 |
| `FNX_HC1` 0 / 5 / 8 | the same as 3 |

Prose2 with the chain fixed (`FNX_DRAFT_ADAPT=0`, no lookup drafts) took 12.10, 14.32, 16.33 and 17.94 ms a round at
1–4 drafts, against the 12.47, 14.76, 16.60 and 18.34 that `Session::generate`'s cost constants were measured from: the
chooser's model holds on this box, and adaptive (142.4 tok/s) matches the best fixed length (2 drafts, 142.8).

Six lanes (`bdecode 6 512`): 313.4 tok/s overall at the default `FNX_BATCH_HORIZON` 4, 322.7 at 2 (one pass each),
306.9 at 8, 304.7 at 16; lookup-only batch drafts 313.6. Each V100's power limit is already its maximum, 250 W.

So on one socket the defaults stand: the ring, two values a word, copy engines one way for prompts, prod's drafts and
batch plan. On the reference
suite (`docs/benchmarks.md`'s scripts) the box measured level with the two-socket one to 12% ahead (six lanes level,
code edit 2–6%, cold reads 4–6%, a warm turn's first token 12%), from the faster links inside each round; the cards'
own kernels are the rest.
