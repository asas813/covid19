from django.shortcuts import render
from datetime import datetime
import pandas as pd
import arrow
import json

# Create your views here.
def home(request):
    dump = covid_dump()
    return render(request, 'chart/covid19.html', {'chart': dump,}, )  # dump를 템플릿에 보내서 처리

def pr_data():
    # 1) covid19 데이터 적재
    df = pd.read_csv('https://raw.githubusercontent.com/datasets/covid-19/master/data/countries-aggregated.csv',
                     parse_dates=['Date'])

    # 2) 분석 대상 국가에 해당하는 행만 선별하여 새로 저장
    countries = ['Korea, South', 'Germany', 'United Kingdom', 'US', 'France']  # 분석 대상 국가
    df = df[df['Country'].isin(countries)]  # 조건을 지정하여 분석 대상 국가 행만 df에 저장

    # 3) 확진자만 합계에 포함하여 수치 계산
    df['Cases'] = df[['Confirmed']].sum(axis='columns')  # 열 방향으로 확진자 합계를 구하여 새로운 열로 저장
    
    # 4) 피봇을 이용하여 데이터 구조 재편하고(확진자 합), 새로운 데이터프레임에 저장
    covid = pd.pivot_table(data=df, index='Date', columns='Country', values='Cases')

    # 4-2) 필요한 특정 열을 columns 로 지정하여 일반 데이터프레임으로 변경
    covid.columns = covid.columns.to_list()
    
    # 5) 인구 십만명당 확진자 비율 계산하기 위하여 인구 데이터 적재
    pop = pd.read_csv('https://datahub.io/JohnSnowLabs/population-figures-by-country/r/population-figures-by-country-csv.csv')
    
    # 6) 인구 데이터에서 분석 대상 국가와 2016년도의 인구 데이터만 추출
    pop = pop[
        pop['Country'].isin(countries)  # 분석 대상 국가 이름과 같거나 (코로나-인구 데이터 국가명 동일한 경우)
        |
        pop['Country'].isin(['United States', 'Korea, Rep.'])  # 미국, 대한민국을 추출 (코로나-인구 데이터 국가명 다를 경우)
    ][['Country', 'Year_2016']]  # 국가 이름 열과 2016년도의 인구 데이터 열만 추출

    # 6-2) 인구 데이터의 국가 이름을 코로나 데이터와 일치하도록 변경하고, 국가 이름 열을 인덱스로 설정
    pop = pop.replace({'United States':'US', 'Korea, Rep.':'Korea, South'})
    pop.set_index(['Country'], inplace=True)

    # 6-3) 인구 데이터를 사전으로 변환하고, 필요한 데이터만 사전으로 추출
    pop = pop.to_dict()  # 사전으로 변환
    populations = pop['Year_2016']  # 필요한 인구 데이터만 사전 형태로 추출

    # 7) 인구 십만명당 확진자 비율 계산
    percapita = covid.copy()  # 확진자 데이터프레임 복사
    for country in percapita.columns.to_list():
        percapita[country] = (percapita[country] / populations[country] * 1000000).round(2)
    
    # 8) 인구 비율 대비 확진자 데이터프레임 반환
    return percapita


def make_my_data(percapita):
    my_data = list()  # 차트에 사용할 데이터 - 리스트 생성

    for country in list(percapita.columns):  # 나라별로 반복하여 데이터 저장
        my_series = list()  # 리스트 생성
        for d in percapita.index.to_list():
            my_series.append(  # arrow 사용하여 날짜 형식 변경
                [arrow.get(d.year, d.month, d.day).timestamp * 1000, round(percapita.loc[d][country], 1)])

        my_dict = dict()  # 딕셔너리 생성
        my_dict['country'] = country   # 국가 이름 저장
        my_dict['series'] = my_series  # 시리즈 내용 저장
        my_data.append(my_dict)  # 딕셔너리 내용을 my_data 에 추가

    return my_data


def make_chart(my_data):
    # 9) highchart
    chart = {
        'chart': {
            'type': 'spline',           # 꺾은선 차트
            'borderColor': '#9DB0AC',   # 선 색상 지정
            'borderWidth': 3,           # 폭 지정
        },
        'title': {'text': '인구 대비 COVID-19 확진자 비율'},  # 제목
        'subtitle': {'text': 'Source: Johns Hopkins University Center for Systems Science and Engineering'},
        'xAxis': {    # x축 데이터 (날짜)
            'type': 'datetime',
        },
        'yAxis': [{   # y축 데이터 (확진자 비율)
            'labels': {   # y축 데이터 포맷 및 스타일 설정
                'format': '{value} 건/백만 명',
                'style': {'color': 'blue'}
            }, 'title': {
                'text': '누적 비율',  # 축 이름 및 스타일 설정
                'style': {'color': 'blue'}
            },
        }, ],
        'plotOptions': {    # 플롯 옵션 지정
            'spline': {
                'lineWidth': 3,  # 선 굵기 지정
                'states': {
                    'hover': {'lineWidth': 5}   # 마우스 호버 시 선 굵기 변경
                },
            }
        },
        'series': list(map(   # 차트 데이터 지정
                    lambda entry: {'name': entry['country'], 'data': entry['series']},
                    my_data)
        ),
        'navigation': {       # 하이차트가 제공하는 메뉴 설정
            'menuItemStyle': {'fontSize': '10px'}
        },
    }
    return chart


def my_converter(o):
    if isinstance(o, datetime):
        return o.__str__()  # 날짜 형식의 데이터를 문자열로 변환하여 반환


def covid_dump():
    df = pr_data()
    my_data = make_my_data(df)
    chart = make_chart(my_data)
    dump = json.dumps(chart, default=my_converter)
    return dump
