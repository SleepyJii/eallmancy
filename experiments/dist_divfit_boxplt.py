import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import polars as pl

def dist_regularised(dist_col):
    return pl.col(dist_col) / pl.col(dist_col).max().over(['problem'])

def fitdivconv_plot(
    df: pl.DataFrame,
    distname: str,
    regularised: bool = False,
    granularity: float = 0.101,
    cutoff: float = 1.5,
    # pass a column name (per-row) or a scalar to draw ±eps
    eps: float | str | None = None,
    nbins: int | None = None,
):
    # --------- data wrangling (Polars) ----------
    if regularised:
        distcol = dist_regularised(f"dist_{distname}")
    else:
        distcol = pl.col(f"dist_{distname}")

    base = (
        df
        .filter(~pl.col("a_elminvalid"), ~pl.col("b_elminvalid"))
        .filter(pl.col("a_fit") != pl.lit(-float("inf")))
        .filter(pl.col("b_fit") != pl.lit(-float("inf")))
        .with_columns(delta_fit=(pl.col("a_fit") - pl.col("b_fit")))
        .with_columns(dist_bin=(distcol / granularity).round() * granularity)
        .filter(pl.col("dist_bin") <= cutoff)
        .select("problem", "dist_bin", "delta_fit", *( [eps] if isinstance(eps, str) else [] ))
    )

    problems = base.select(pl.col("problem").unique()).to_series().to_list()
    problems = [p for p in problems if p is not None]
    n = len(problems)
    if n == 0:
        raise ValueError("No data after filtering.")

    # row heights: for each facet -> [box (big), hist (short)]
    row_heights = []
    specs = []
    for _ in problems:
        row_heights += [0.80, 0.20]
        specs += [[{"type":"xy"}], [{"type":"xy"}]]

    fig = make_subplots(
        rows=2*n, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=row_heights, specs=specs,
        # subplot_titles=[f"{p}" for p in problems for _ in (0,1)]
    )

    palette = px.colors.qualitative.Plotly
    color_map = {p: palette[i % len(palette)] for i, p in enumerate(problems)}

    # --------- traces ----------
    for i, p in enumerate(problems, start=1):
        r_box = 2*i - 1  # row for box
        r_hist = 2*i     # row for histogram

        dfp = base.filter(pl.col("problem") == p)

        # box (same as px.box aesthetics)
        fig.add_trace(
            go.Box(
                x=dfp["dist_bin"].to_list(),
                y=dfp["delta_fit"].to_list(),
                name=p,
                marker_color=color_map[p],
                legendgroup=p,
                showlegend=True,
                boxpoints=False,
                whiskerwidth=0,
                showwhiskers=False,
                quartilemethod="inclusive"
            ),
            row=r_box, col=1
        )

        # histogram strip below (occurrence density per bin)
        # using Histogram so the binning matches the box x-bins visually
        fig.add_trace(
            go.Histogram(
                x=dfp["dist_bin"].to_list(),
                nbinsx=None,#nbins,  # keep None to let plotly choose
                marker_line_width=0,
                name=f"{p} density",
                showlegend=False,
                histnorm='probability',
                marker_color=color_map[p],   # <-- same as box
                opacity=0.4,                 # <-- adjust transparency
            ),
            row=r_hist, col=1
        )

        # y±eps reference lines on the BOX row only
        if eps is not None:
            eps_val = float(dfp.select(pl.col(eps).mean()).item()) if isinstance(eps, str) else float(eps)
            if eps_val > 0:
                for yv in (+eps_val, -eps_val):
                    fig.add_hline(
                        y=yv, row=r_box, col=1,
                        line_dash="dash", line_color="gray", opacity=0.7
                    )

        # tidy axis labels per facet
        q15 = dfp.select(pl.col.delta_fit.quantile(0.15)).item()
        q85 = dfp.select(pl.col.delta_fit.quantile(0.85)).item()
        fig.update_yaxes(range=[q15, q85], row=r_box, col=1) # TODO: actually provide
        fig.update_yaxes(title_text="Δ fit", row=r_box, col=1, zeroline=True)
        fig.update_yaxes(title_text="density", row=r_hist, col=1, showgrid=False)

    # right-side facet labels like px facet_row
    for i, p in enumerate(problems, start=1):
        r_box = 2*i - 1
        fig.add_annotation(
            text=p,
            xref="paper", x=1.01,                 # right of plotting area
            yref=f"y{r_box if r_box>1 else ''} domain", y=0.5,       # middle of the box row
            xanchor="left", yanchor="middle",
            textangle=90,
            showarrow=False, font=dict(size=12)
        )
    for i in range(1, n+1):
        r_box, r_hist = 2*i - 1, 2*i
        fig.update_xaxes(showticklabels=False, title_text=None, row=r_box, col=1)
        # hide dist_bin title on all hist rows except the last
        fig.update_xaxes(title_text=None, row=r_hist, col=1)
    # put a single x-title on the very bottom subplot
    fig.update_xaxes(title_text="dist_bin", row=2*n, col=1)
    
    # global x axis
    fig.update_xaxes(type="linear", matches=None)

    # style tweaks to resemble your px.box settings
    fig.update_layout(
        height=max(350, 220*n),  # scale with facets
        title=f"[{distname}] DivFit Convergence",
        boxmode="overlay",
        boxgap=0, boxgroupgap=0,
        bargap=0,  # tighter hist bars
        margin=dict(t=60, r=20, b=40, l=60)
    )
    return fig
