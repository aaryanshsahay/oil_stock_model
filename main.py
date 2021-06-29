#base
import time
import pandas as pd
#web//scrarping
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import requests
#stock data 
import yfinance as yf
#sentiment//nlp
from textblob import TextBlob
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
#misc
import keyboard
import re

start=time.time()
sia=SentimentIntensityAnalyzer()

main_url='https://oilprice.com/Energy/Crude-Oil/'

def get_all_links(main_url):
	'''
	*)scrapes all the links of articles on the main home page of the site and stores
	the links in a list.

	*)Returns a list which contains all the links of the articles.

	'''

	driver=webdriver.Firefox()
	
	driver.get(main_url)
	
	print('Website reached successfully')
	#to get rid of popup
	print('Pressing enter')
	keyboard.press_and_release('enter')
	print('Pressed enter')
	time.sleep(3)
	
	req=requests.get(main_url)
	soup=BeautifulSoup(req.text,'lxml')
	#div which contains all the articles
	all_divs=soup.find('div',class_='tableGrid__column tableGrid__column--articleContent category')
	print('Found correct div')
	url_list=[]
	count=0
	print('Getting all links')
	#getting the links stored in the div
	for link in all_divs.find_all('a',attrs={'href':re.compile("^https://")}):
		a=str(link.get('href'))
		url_list.append(a)
		count+=1
		#breaking loop on reaching the last article of the page
		if count==40:
			break
	
	print('Successfull')
	#the links have been added twice , getting rid of duplicate values by dropping alternate elements.
	url_list=[url_list[i] for i in range(len(url_list)) if i%2!=0]
	
	return url_list

def get_article_data(url):
	'''
	*)using the links stored in the get_all_links() funciton to get the data in article.
	
	*)cleaning it (removing whitespace and line breaks etc)

	*)returns the contents of the article and the date on which it was written.

	'''
	#getting article content
	req=requests.get(url)
	soup=BeautifulSoup(req.text,'lxml')
	para_content=soup.find('div',class_='wysiwyg clear')
	para_text=para_content.find_all('p')

	res=[]

	output=[i.text for i in para_text]
	output1=[]

	for j in output:
		j=j.replace('\n','')
		output1.append(j)

	for j in range(len(output1)):
		res.append(output1[j-2])

	res.pop(0)
	res.pop(0)

	article=''
	article=article.join(res)
	#getting article date
	date_text=soup.find('span',class_='article_byline').text
	date_text=date_text.split()
	date=date_text[-6]+' '+date_text[-5]+' '+date_text[-4]
	date=date.replace(',','')


	return article,date
	
def convert_date(date):
	'''
	*)Converts date from Jun 28,2021 -> 2021-06-28 which makes it useful to pass in the yfinance library.

	*)returns date in format YYYY-MM-DD(string)

	'''
	date_dict={'jan':'01','feb':'02','mar':'03','apr':'04','may':'05','jun':'06','jul':'07','aug':'08','sep':'09','oct':'10','nov':'11','dec':'12'}
	initial_date=date.split()
	initial_date[0]=initial_date[0].lower()
	initial_date[0]=date_dict[initial_date[0]]
	res_date=str(initial_date[2])+'-'+str(initial_date[0])+'-'+str(initial_date[1])

	return res_date


def get_stock_data(dates_list):
	'''
	*)using yfinance library

	*)generates a dataframe based on a list of dates.

	*)returns dataframe

	'''
	key='cl=f' #crude oil symbol
	crude=yf.Ticker(key).history(period='max')
	
	#since the 'date' is an index, changing it to a column.
	crude['Date']=crude.index
	crude.reset_index(drop=True,inplace=True)
	cols=['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits','Date']
	
	#rearranging columns
	cols=cols[-1:]+cols[:-1]
	crude=crude[cols]
	
	#uncomment below line to drop Dicidends and Stock Splits columns.

	#crude=crude.drop(['Dividends','Stock Splits'],axis=1)
	crude=crude[crude['Date'].astype(str).isin(dates_list)]
	crude['Date']=crude['Date'].astype(str)

	return crude
	

def get_polarity_score(article):
	'''
	*)performing sentiment analysis

	*)textblob and nltk (SentimentIntensityAnalyzer)
	
	*)value positive then sentiment positive else vice versa, value 0 then neutral sentiment.
	
	*)returns textblob score and nltk score
	'''
	
	#textblob
	analysis=TextBlob(article).sentiment
	score=analysis.polarity
	
	#nltk
	score1=sia.polarity_scores(article)
	score_=score1['compound']
	
	return score,score_

def make_df(article_data,article_date,textblob_scores,nltk_scores):
	'''
	*)generates a df which contains article info like content,date and the polarity scores.

	*)returns dataframe 
	'''
	article_data=pd.Series(article_data)
	article_date=pd.Series(article_date)
	textblob_scores=pd.Series(textblob_scores)
	nltk_scores=pd.Series(nltk_scores)
	

	data={'Content':article_data,'Date':article_date,'Textblob Score':textblob_scores,'NLTK Score':nltk_scores}
	df=pd.DataFrame(data)

	return df


def main():
	'''
	*)main function, all individual components are combined here.

	*)returns a dataframe which contains stock data along with article data.
	'''

	#defining lists
	article_data_list=[]
	article_date_list=[]
	textblob_scores=[]
	nltk_scores=[]

	#getting all links
	all_links=get_all_links(main_url)
	
	#adding values to list
	for i in all_links:
		data,date=get_article_data(i)
		article_data_list.append(data)
		date=convert_date(date)
		article_date_list.append(date)

	#getting polrity scores
	for i in article_data_list:
		a,b=get_polarity_score(i)
		textblob_scores.append(a)
		nltk_scores.append(b)

		
	#getting stock data
	stock_data=get_stock_data(article_date_list)


	
	#making article dataframe
	df=make_df(article_data_list,article_date_list,textblob_scores,nltk_scores)

	#commented, used for debugging purposes.
	#print(df.head())
	#print(stock_data.head())
	
	#merging two dataframes to get desired dataframe
	final_df=pd.merge(df,stock_data,how="outer",on=['Date'])

	return final_df.head()




print(main())
end=time.time()
print('Time Taken:',end-start)
