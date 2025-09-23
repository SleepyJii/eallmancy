import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import polars as pl

def dist_regularised(dist_col):
    return pl.col(dist_col) / pl.col(dist_col).max().over(['problem'])

def fitdivconv_plot_multi(
    df: pl.DataFrame,
    distnames: list[str],                      # <-- multiple metrics
    regularised: bool = False,
    granularity: float = 0.101,
    cutoff: float = 1.5,
    eps: float | str | None = None,
    nbins: int | None = None,
):
    # unique problems
    problems = (
        df.select(pl.col("problem").unique()).sort(['problem'])
          .to_series().to_list()
    )
    problems = [p for p in problems if p is not None]
    n, m = len(problems), len(distnames)
    if n == 0 or m == 0:
        raise ValueError("Need at least one problem and one distance name.")

    # subplot grid: for each problem -> [box, hist] rows, across m columns
    row_heights = [0.80, 0.20] * n
    specs = [[{"type":"xy"} for _ in range(m)] for _ in range(2*n)]
    fig = make_subplots(
        rows=2*n, cols=m, shared_xaxes=True, shared_yaxes=False,
        vertical_spacing=0.03, horizontal_spacing=0.06,
        row_heights=row_heights, specs=specs
    )

    # colors by problem
    palette = px.colors.qualitative.Plotly
    color_map = {p: palette[i % len(palette)] for i, p in enumerate(problems)}

    # one column per distance metric
    for j, distname in enumerate(distnames, start=1):
        # --- prepare per-metric data (keeps your Polars pipeline) ---
        distcol = (dist_regularised(f"dist_{distname}")
                   if regularised else pl.col(f"dist_{distname}"))
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

        # add traces per problem
        for i, p in enumerate(problems, start=1):
            r_box, r_hist = 2*i - 1, 2*i
            dfp = base.filter(pl.col("problem") == p)

            # box (legend only in first column so it doesn't repeat)
            fig.add_trace(
                go.Box(
                    x=dfp["dist_bin"].to_list(),
                    y=dfp["delta_fit"].to_list(),
                    name=p,
                    legendgroup=p,
                    marker_color=color_map[p],
                    showlegend=(j == 1),      # legend once
                    boxpoints=False,
                    whiskerwidth=0,
                    showwhiskers=False,
                    quartilemethod="inclusive",
                ),
                row=r_box, col=j
            )

            # histogram strip
            fig.add_trace(
                go.Histogram(
                    x=dfp["dist_bin"].to_list(),
                    nbinsx=nbins,
                    marker_line_width=0,
                    marker_color=color_map[p],
                    opacity=0.4,
                    showlegend=False,
                    histnorm="probability",
                    name=f"{p} density",
                ),
                row=r_hist, col=j
            )

            # ±eps reference lines (box row only)
            if eps is not None and len(dfp) > 0:
                eps_val = (float(dfp.select(pl.col(eps).mean()).item())
                           if isinstance(eps, str) else float(eps))
                if eps_val > 0:
                    for yv in (+eps_val, -eps_val):
                        fig.add_hline(y=yv, row=r_box, col=j,
                                      line_dash="dash", line_color="gray", opacity=0.7)

            # y-range & labels
            if len(dfp) > 0:
                q15 = dfp.select(pl.col.delta_fit.quantile(0.20).over(['dist_bin']).min()).item()
                q85 = dfp.select(pl.col.delta_fit.quantile(0.80).over(['dist_bin']).max()).item()
                fig.update_yaxes(range=[q15, q85], row=r_box, col=j)
            fig.update_yaxes(title_text="Δ fit", row=r_box, col=j, zeroline=True)
            fig.update_yaxes(title_text="density", row=r_hist, col=j, showgrid=False)

            # x labels: hide everywhere except bottom row of this column
            fig.update_xaxes(showticklabels=False, title_text=None, row=r_box, col=j)
            fig.update_xaxes(title_text=None, row=r_hist, col=j)

        # column title (metric name) centered above this column
        # fig.add_annotation(
        #     text=distname, xref=f"x{j if j>1 else ''} domain", x=0.5,
        #     yref="paper", y=1.06, showarrow=False, font=dict(size=12)
        # )

    # right-side facet labels (only on the last column, box rows)
    last_col = m
    # for i, p in enumerate(problems, start=1):
    #     r_box = 2*i - 1
    #     yref = "y domain" if (r_box == 1 and last_col == 1) else f"y{(r_box-1)*m + last_col} domain"
    #     fig.add_annotation(
    #         text=p, xref="paper", x=1.01,
    #         yref=yref, y=0.5,
    #         xanchor="left", yanchor="middle",
    #         textangle=90, showarrow=False, font=dict(size=12)
    #     )
    for j in range(2, m+1):   # all columns except the first
        for i in range(1, n+1):
            r_box, r_hist = 2*i - 1, 2*i
            fig.update_yaxes(title_text=None, row=r_box, col=j)
            fig.update_yaxes(title_text=None, row=r_hist, col=j)
    # force x-axes to range 0..1 for all subplot columns/rows
    for j in range(1, m+1):
        for i in range(1, 2*n + 1):
            fig.update_xaxes(range=[0.-granularity, 1.+granularity], row=i, col=j)


    # bottom x-titles per column (use metric name or 'dist_bin')
    for j, distname in enumerate(distnames, start=1):
        fig.update_xaxes(title_text=distname, row=2*n, col=j)

    fig.update_xaxes(type="linear", matches=None)
    fig.update_layout(
        height=max(350, 280*n),
        title=f"ΔFitness 25th-75th Quantile Convergence with Distance" + ("" if not regularised else ", Regularised"),
        boxmode="overlay",
        boxgap=0, boxgroupgap=0, bargap=0,
        margin=dict(t=80, r=60, b=50, l=60),
        legend=dict(title="", tracegroupgap=4)
    )
    fig.update_layout(
    legend=dict(
        orientation="h",   # horizontal
        yanchor="bottom",
        y=-0.15,           # adjust this to move further/closer
        xanchor="center",
        x=0.5
        )
    )

    return fig
