# -*- coding: utf-8 -*-
"""
1. Most recent statistics (total confirmed, total deaths, death rate, biggest change)
Created on Mon Mar 30 23:44:26 2020

@author: jerin
"""

import pandas as pd
import requests

from zipfile import ZipFile
from io import TextIOWrapper, BytesIO

import matplotlib.pyplot as plt


def get_data():
    covid_url = "https://nssac.bii.virginia.edu/covid-19/dashboard/data/nssac-ncov-data-country-state.zip"
    resp = requests.get(covid_url, verify=False)
    data_zip = ZipFile(BytesIO(resp.content))

    collect = []
    for daily_filename in data_zip.namelist():
        if "README" in daily_filename:
            continue
        zipped_csv = TextIOWrapper(data_zip.open(daily_filename))

        daily_df = pd.read_csv(zipped_csv)
        daily_df["Date"] = daily_filename[-14:-4]
        collect.append(daily_df)
    data = pd.concat(collect, sort=False, ignore_index=True)

    return data


def clean_data(df):
    df = df.drop(columns="Last Update")
    df = df.rename(columns={"name": "Area", "Region": "Country",})
    df = df[["Area", "Country", "Date", "Confirmed", "Deaths", "Recovered"]]

    df["Date"] = pd.to_datetime(df.Date)
    df["Country"] = df.Country.str.strip()

    return df


def get_country_series(df, country="USA"):
    country_sum = clean_covid.groupby(["Country", "Date"]).sum().reset_index()
    country = country_sum[country_sum.Country == country]
    return country


covid_data = get_data()
clean_covid = clean_data(covid_data)


test = covid_data.Date.apply(lambda x: x[-5:])

us_confirmed = pd.read_csv(
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"
)

us_deaths = pd.read_csv(
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv"
)


def format_df(raw, name):
    states_df = raw.groupby("Province_State").sum().reset_index()
    df = states_df.melt(
        id_vars="Province_State",
        value_vars=[i for i in states_df.columns if i.endswith("20")],
        var_name="Date",
        value_name=name,
    )

    df = df.pivot_table(
        index="Date", columns="Province_State", values=name
    ).reset_index()
    df["Date"] = pd.to_datetime(df.Date)
    df = df.sort_values("Date").set_index("Date")
    # df = df.cumsum()
    df[["Maryland", "New Jersey", "New York", "Virginia", "Washington"]].plot()
    df["US"] = df.sum(axis=1)
    return df


confirmed = format_df(us_confirmed, "Confirmed")
deaths = format_df(us_deaths, "Deaths")

# Fix data entry error for Hawaii
deaths.loc["3/25/2020":"3/31/2020", "Hawaii"] = 1

daily_confirmed = confirmed.diff()
daily_deaths = deaths.diff()

# =============================================================================
# Average cases a day on a weekly basis
# =============================================================================
fig, ax = plt.subplots(1)
confirmed.US.diff().resample("W", closed="left", label="left").mean().plot(
    ax=ax, label="Confirmed"
)
deaths.US.diff().resample("W", closed="left", label="left").mean().plot(
    ax=ax, label="Deaths"
)
ax.legend()
ax.set_title("Average Cases Per Day")


combine = confirmed[["US"]].join(deaths[["US"]], rsuffix="_deaths")
combine.columns = ["Confirmed", "Deaths"]
combine["DeathRate"] = combine.Deaths / combine.Confirmed

combine.DeathRate.plot()


pop = pd.read_html("https://worldpopulationreview.com/")
popdf = pop[0].iloc[:, 1:3]
popdf.columns = ["Country", "Population"]
popdf["Country"] = popdf.Country.replace(
    {"United States": "US", "South Korea": "Korea, South"}
)

df = pd.read_csv(
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
)
df = df.drop(columns=["Lat", "Long"])
df = df.rename(columns={"Province/State": "Area", "Country/Region": "Country"})

df = df.groupby("Country").sum().reset_index()

df = df.melt(id_vars="Country", var_name="Date", value_name="Deaths")
df["Date"] = pd.to_datetime(df.Date)
df = df.query("Deaths > 0")
df = df.sort_values(["Country", "Date"])
df["FromFirstDeath"] = df.groupby("Country").cumcount()
df = df.merge(popdf, how="left", on="Country")
df["PopMil"] = df.Population / 1000000
df["DeathsPerMil"] = df.Deaths / df.PopMil

df = df.pivot_table(index="FromFirstDeath", columns="Country", values="DeathsPerMil")
df = df.rename(columns={"Korea, South": "South Korea", "US": "USA"})

chart_data = df[
    [
        "USA",
        "Spain",
        "France",
        "United Kingdom",
        "Brazil",
        "Italy",
        "Canada",
        "Germany",
        "Russia",
        "India",
        "Japan",
        "South Korea",
    ]
]

fig, ax = plt.subplots(figsize=(13, 8))
chart_data.plot(ax=ax)
ax.get_legend().remove()
