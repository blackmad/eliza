import spacy

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.metrics import accuracy_score
  
vader = SentimentIntensityAnalyzer()
def vader_polarity(text):
    """ Transform the output to a binary 0/1 result """
    score = vader.polarity_scores(text)
    return 1 if score['pos'] > score['neg'] else 0

# default_conjugator.conjugate("fuck").conjug_info['indicative']['indicative present continuous']['2p 2p']


# doc = nlp("Wall Street Journal just published an interesting piece on crypto currencies")
# for chunk in doc.noun_chunks:
#     print(chunk.text, chunk.label_, chunk.root.text)


nlp = spacy.load('en_core_web_sm')

import mlconjug
default_conjugator = mlconjug.Conjugator(language='en')

verbs = {}
for l in open('lib/en-verbs.txt'):
    parts = l.split(',')
    verbs[parts[0]] = parts

class ElizaHelpers:
    
    @staticmethod
    def remove_punctuation(text):
        for punct in [',', '.', ';']:
            if punct in text:
                text = text[:text.index(punct)]
        return text


    @staticmethod 
    def conjugate_to_gerund(word):
        if word in verbs:
            return verbs[word][5]
        else:
            return default_conjugator.conjugate(word).conjug_info['indicative']['indicative present continuous']['2p 2p']


    @staticmethod
    def reconjugate_to_gerund(text):
        doc = nlp(text)

        results = []
        for token in doc:
            if token.tag_ == 'TO':
                next
            elif token.pos_ == 'VERB':
                results.append(ElizaHelpers.conjugate_to_gerund(token.text))
            else:
                results.append(token.text)
    # print(token.text, token.lemma_, token.pos_, token.tag_, token.dep_,
            #     token.shape_, token.is_alpha, token.is_stop)
    
        return results
                