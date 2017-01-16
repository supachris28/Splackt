#usage:
#call get_title with a string of some kind 
#will return an array of the titles most closely matching that string




import dbapi

db = dbapi.dbs(l=False, s=False)


def levenshteinDistance(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

get_book_ids = '''
select
*,
TRIM(BOTH ' ' FROM substring_index(LOWER(title), '[',1)) 
from
home.dim_products
where title is not null
and type != 'ebooks'
'''

cols = [
"isbn13",
"nid",
"published_date",
"product_nid",
"type",
"title",
"author",
"website_scope",
"website_category",
"series",
"isbn10",
"length",
"image_url",
"book_url",
"simple_title",
]


def get_title(string, titles = []):
	string = string.split('[')[0].lower().strip()
	if titles == []:
		print ('grabbing title data')
		titles.extend(map(
						lambda x: dict(zip(cols,x)),
						db.p.ex(get_book_ids)
					)
			)
	for i in titles:
		i['dist'] = levenshteinDistance(i['simple_title'], string)
	matches = sorted(titles, key = lambda x: x['dist'])[:5]
	if matches[0]['dist'] == 0:
		#print ('found an exact match!')
		return [matches[0]]
	else:
		return matches





