# Financial mathematics and implementation map

All examples use decimal returns, not percentages. N denotes observations/year, n the number of return observations. Default N=252 assumes daily trading sessions; changing N does not resample a series. Input panels must have identical dates and horizons, increasing unique indexes, no missing/nonfinite values and positive adjusted prices. Price adjustment is the provider's responsibility.

## Returns — app/research/returns.py

Simple return: `R_t = P_t / P_(t-1) - 1`. Log return: `r_t = log(P_t/P_(t-1)) = log(1+R_t)`. Wealth: `W_t = product_(s<=t)(1+R_s)` starting at one. Cumulative return: `W_n-1`.

Example: 100 → 110 → 99 gives +10%, −10%, final −1%; summing returns would incorrectly give zero. The implementation disables Pandas filling and discards only the initial undefined return. Empty/single-price/nonpositive/missing prices raise ValueError. Wealth can be zero after −100%; returns below −100% are invalid for the unlevered model. Log returns require strictly positive wealth ratios.

## Annualization

`CAGR_observation = W_n^(N/n)-1`; `sigma_ann = sample_std(R)*sqrt(N)`. The standard deviation denominator is n−1. Example: two returns +10%, −10%, with N=2 gives annualized −1%; sample volatility is approximately 14.142%, annualized 20%.

Implementation: `returns.annualized_return`, `risk.metrics`. This is observation-count annualization, not a day-count CAGR. Missing sessions or weekly data mislabeled as daily invalidate it. Square-root annualization assumes sufficiently stable weak dependence and may understate risk with serial correlation. At least two returns are required for risk estimates.

## Risk-free conversion and Sharpe

`rf_daily = (1+rf_annual)^(1/N)-1`; excess `e_t=R_t-rf_daily`; `Sharpe = mean(e)/sample_std(e)*sqrt(N)`.

Example: excess daily mean .001, standard deviation .01 and N=252 gives about 1.587. Implementation: `risk.metrics`. Annual_rf must exceed −1. Zero/near-zero denominator gives null; it is not a perfect score. Historical Sharpe is uncertain, sensitive to frequency, sample, serial correlation, skew and outliers. The general asset metrics use the selected constant annual risk-free assumption; factor regressions instead consume the dataset's dated risk-free observations.

## Downside deviation and Sortino

`DD = sqrt(mean(min(R_t-rf_daily,0)^2))`; `DD_ann=DD*sqrt(N)`; `Sortino=mean(e)/DD*sqrt(N)`.

Example: e=[.1,−.1,.05,−.02] gives DD=sqrt((.01+.0004)/4). The denominator averages over all four periods, not only the two losing periods. Target is risk-free, explicitly chosen. No downside gives null. Implemented in `risk.metrics` and tested by hand.

## Drawdown and Calmar

`H_t=max(1,W_1,...,W_t)`; `D_t=W_t/H_t−1`; `MDD=min(D_t)`; `Calmar=CAGR/abs(MDD)`.

Example: initial wealth 1 drops to .8 then recovers to 1: drawdown −20%, then zero. An initial loss must not be missed by starting the high-water mark at .8. `drawdown.episodes` tracks peak, first underwater observation, trough, recovery and underwater observation count. Peak null means pre-sample initial wealth. Recovery null means still underwater. Ties use the first lowest trough; recovered peak dates update. Duration is observations, not calendar days. A zero maximum drawdown makes Calmar undefined.

## Historical VaR and expected shortfall

Define losses `L_t=−R_t`. At confidence c, `VaR_c=quantile_c(L)`, using linear interpolation. `ES_c=mean(L_t where L_t>=VaR_c)`.

Example: returns [−.10,−.02,.01,.03] → losses [.10,.02,−.01,−.03]. The 95% quantile is .088 and ES is .10. For very small samples, ES may be a single observation. Atoms/ties and interpolation choices affect tail estimates. All-positive samples may give negative VaR; signed output is deliberate. Not a prediction of maximum loss. `risk.metrics` validates confidence and reports one-observation-horizon losses.

## Benchmark beta and alpha

`beta=cov(R,B)/var(B)`; regression intercept `alpha_daily=mean(R-rf)-beta*mean(B-rf)`; `alpha_ann_arithmetic=N*alpha_daily`.

Example: R=.001+1.5B recovers beta=1.5 and daily alpha=.001. It is a descriptive regression identity, not skill or a causal conclusion. Variances use matching sample conventions and exact aligned dates. Constant benchmark → beta/alpha null. Arithmetic annual alpha is not geometric return. Implemented in `risk.metrics` for one factor; `factors.regress` handles multiple factors.

## Tracking error, information ratio and active return

Active daily return `a_t=R_t-B_t`; `TE=sample_std(a)*sqrt(N)`; `IR=mean(a)/sample_std(a)*sqrt(N)`. Reported cumulative active return is `product(1+R)-product(1+B)`, not sum of daily active returns and not the relative wealth ratio.

Example: identical returns → zero TE, zero cumulative active return, undefined IR (0/0). `risk.metrics` rejects mismatched dates rather than silently choosing different horizons. Relative drawdown is separately computed on relative wealth increments `(1+R)/(1+B)-1`.

## Upside/downside capture

Select periods with B>0 for upside, B<0 for downside. Compute the ratio of geometric mean R to geometric mean B over selected periods. Example: R=.02 and B=.01 for each up period gives upside capture 2.0 (200%). Empty subsets or zero benchmark geometric mean give null. Ratio units differ from percentage points; downside signs require careful interpretation. This geometric-mean convention is explicit and may differ from annualized vendor capture measures.

## Portfolio return, covariance and risk contribution

Beginning weights `w_(t-1)` and cash weight c give `R_p,t=sum(w_i,t-1*R_i,t)+c*rf_t`. The covariance projection at target weights is `var_p=w'Σw`, `sigma_p=sqrt(w'Σw)`. With annual covariance `Σ_ann=N*Σ_daily`, component volatility `RC_i=w_i*(Σ_ann*w)_i/sigma_p` sums to annual portfolio volatility.

Example: two equally weighted assets with volatilities 20% and 10%, correlation zero: variance .25*.04+.25*.01=.0125; volatility about 11.18%, not average volatility 15%. Perfect negative correlation can reduce covariance risk substantially but is not stable diversification evidence. Zero variance yields zero contributions. `risk.covariance_risk` validates weights and dimensions. It projects fixed target weights; it does not replace realized drifting-weight path risk.

## Rebalancing, drift and trading cost

After return, risky weights drift to `w_i*(1+R_i)/(1+R_p)`; cash similarly drifts. Scheduled rebalancing resets weights. Turnover `T=sum(abs(target_i-current_i))`; cost fraction `c=T*bps/10000`. Net return `(1-c)*(1+gross)-1`. Example: 100 bps initial entry cost and gross 5% gives .99*1.05−1=3.95%.

`portfolio.simulate` charges risky trades only, includes entry and no assumed terminal sale, caps risky exposure at one and pays cash the configured risk-free return. Uniform proportional cost scaling assumes the target allocation is achievable after costs; exact execution accounting and market impact are deferred. Input scheduled targets are beginning-interval holdings, not contemporaneous signals.

## Factor OLS and HAC inference

`R_i,t-rf_t = alpha + beta'F_t + epsilon_t`; minimize squared residuals. Full-rank OLS solution conceptually `(X'X)^(-1)X'y`; statsmodels uses numerically appropriate linear algebra rather than hand-inverting. R² measures in-sample explained variation. Standard errors use HAC with configurable lag count (default 5); coefficients, t-values, p-values, 95% intervals and residual sample volatility are reported.

Example: simulated `y=.0002+1.2*market-.5*value+noise` recovers those exposures within tolerances. Need at least max(20,3×parameters) observations and full column rank. Missing dates/factors/risk-free values reject the run. HAC inference is asymptotic, not proof of significance in a small sample. Factors must have correct return/excess-return definitions and units. Regression is not causation; multicollinearity, omitted variables, multiple testing and changing exposures remain concerns.

## Attribution

Single-period security contribution `C_i=w_i*R_i`. For multiple periods, use prior net wealth times post-cost asset contribution: `C_i,total=sum(W_(t-1)*(1-cost_t)*w_i,t-1*R_i,t)`. Cash follows the same scaling; cost contribution is `-sum(W_(t-1)*cost_t)`. Their sum equals final net wealth minus one. Example: buy-and-hold 50/50 assets going 100→200→200 and 100→100→200 each contribute .5, total 1 (100%).

Brinson–Fachler single-period allocation `(wp-wb)*(rb-R_B)`; selection `wb*(rp-rb)`; interaction `(wp-wb)*(rp-rb)`. Sum equals `R_P-R_B` when weights each sum to one. Inputs are aligned category weights and category returns, not arbitrary security factor loadings. `attribution.brinson` is a tested library function; dashboard reports security wealth-linked contributions. Multi-period Brinson linking is not implemented.

## Rolling and statistical diagnostics

Window total return compounds; volatility/Sharpe use the full window, beta uses window covariance and benchmark variance. Rolling drawdown resets initial wealth to one at each window start. Insufficient warmup observations remain null.

Sample mean/variance, median and percentiles summarize distributions; skew describes asymmetry; kurtosis is excess kurtosis (normal=0). Jarque–Bera is reported for at least eight nonconstant observations, with strong caution about finite samples and dependence. QQ compares empirical ordered returns with theoretical normal quantiles. Flat series has undefined skew/kurtosis; it does not prove normality. `statistics.diagnostics`, `rolling.rolling_metrics` implement these calculations.
