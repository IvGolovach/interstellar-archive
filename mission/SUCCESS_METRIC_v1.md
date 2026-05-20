# SUCCESS_METRIC_v1

## 1. Definitions

Mission success probability is defined as:

\[
P_{success} = P_{hit} \times P_{survive} \times P_{data\_intact}
\]

with acceptance rule:

\[
\text{success} = \left(P_{success} \ge \text{success\_threshold}\right)
\]

`success_threshold` is user-configurable in `[0, 1]`.

## 2. Hit probability `P_hit`

Geometric crossing condition is `r \le r_s` where:

\[
r_s = \frac{2GM}{c^2}
\]

Define miss distance and effective uncertainty:

\[
d_{miss} = \max(0, r - r_s)
\]

\[
\sigma_{eff} = \sqrt{\sigma_{nav}^2 + (r\,\sigma_{guidance})^2 + (r\,\epsilon_{exec}\,10^{-3})^2}
\]

Then:

\[
P_{hit} = \exp\left(-\frac{1}{2}\left(\frac{d_{miss}}{\sigma_{eff}}\right)^2\right)
\]

If `d_miss = 0`, `P_hit = 1` in this v1 proxy.

## 3. Survival probability `P_survive`

Hazard ratios:

\[
h_F = \frac{F_{rad}}{F_{rad,max}}, \quad
h_\rho = \frac{\rho_{plasma}}{\rho_{plasma,max}}, \quad
h_S = \frac{S_{dust}}{S_{dust,max}}
\]

Combined hazard in v1:

\[
h_{max} = \max(h_F, h_\rho, h_S)
\]

with material degradation term `\mu_{deg}`:

\[
P_{survive} = \mathbb{1}(\text{environment\_acceptable})\,\exp\left(-0.8\,h_{max} - \mu_{deg}\right)
\]

Minimum modeled factors in v1: dust proxy, radiation proxy, plasma proxy, material degradation proxy.

## 4. Data integrity probability `P_data_intact`

v1 treats data integrity as a reduced-order physical-media survivability proxy (not bit-level ECC and not a direct persistence measurement).

\[
P_{data\_intact} = \mathrm{clip}_{[0,1]}\left(m_{media}\,\exp(-0.6\,h_F)\,(1-\mu_{deg})\right)
\]

where `m_media` is `data_media_survival_margin`.

## 5. Output fields required

- `p_hit`
- `p_survive`
- `p_data_intact`
- `p_success`
- `success_threshold`
- `success`

All are required in the deterministic mission baseline output structure.
