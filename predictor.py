# coding: utf-8

print('********************************')
print('***** Running predictor.py *****')
print('********************************')

from classifyintents import survey
from os.path import basename, join, splitext
import pandas as pd
import numpy as np
import pickle, sys

# Handle command line arguments

input_file = sys.argv[1]
model = sys.argv[2]

def main():
    
    # Instantiate an instance of the survey class.
    
    intent = survey()

    intent.load(input_file)

    # Clean the raw dataset. This creates a dataframe called `intent.data`.

    intent.clean_raw()

    # Apply cleaning rules to URLs and extract unique. These are stored in `intent.unique_pages`

    intent.clean_urls()

    # Now perform an API lookup on the cleaned URLS, and match them back into `intent.data`. This is quite verbose!

    intent.api_lookup()

    # Remove obvious `none` cases where there is no free text.

    no_comments = (intent.data['comment_further_comments'] == 'none') & (intent.data['comment_where_for_help'] == 'none') & (intent.data['comment_other_where_for_help'] == 'none') & (intent.data['comment_why_you_came'] == 'none')
    easy_nones = intent.data.loc[no_comments,'respondent_ID'].astype(int)

    # Don't bother trying to classify easily classificable nones 

    intent.data = intent.data.loc[~no_comments]

    # Now run the predictor class

    intent.predictor()

    # Import the saved model object from the training notebook

    exported_pipeline = pickle.load(open(model,'rb'))

    # Run the prediction

    predicted_classes = exported_pipeline.predict(intent.cleaned)

    print(np.bincount(predicted_classes))

    pd.Series(predicted_classes).to_csv('predicted_classes.csv')
    
    # Convert to a Series, name, and combine the respondent_ID with the predicted code. Then strip out those cases who are not coming out as OKs

    predicted_classes = pd.Series(predicted_classes, index=intent.cleaned.index, name='ada_code')
    predicted_classes = pd.concat([intent.data['respondent_ID'].astype('int'), predicted_classes], axis=1)
    predicted_classes = predicted_classes.loc[predicted_classes['ada_code'] == 1,'respondent_ID']

    # Combine the predicted OKs with the easily classified OKs.

    final_oks = pd.concat([easy_nones, predicted_classes], axis = 0)

    # Finally, use `final_oks` to remove the OKs from `intent.raw`, and save it out to CSV for manual classification

    intent.raw['code'] = ''
    intent.raw.loc[intent.raw['RespondentID'].isin(predicted_classes),'code'] = 'ok'
    intent.raw.loc[intent.raw['RespondentID'].isin(easy_nones),'code'] = 'none'
    
    intent.raw['RespondentID'] = intent.raw['RespondentID'].astype('int')
    intent.data['respondent_ID'] = intent.data['respondent_ID'].astype('int')   
    
    output = intent.raw.merge(
            right=intent.data.loc[:,['respondent_ID','page','section','org']],
            how='left',
            left_on='RespondentID',
            right_on='respondent_ID'
            )

    output_file = join(
            'output_data/classified',
            splitext(basename(input_file))[0] + '_classified.csv'
            )

    print('***** Saving predictions to ', output_file, ' *****')    

    output.to_csv(output_file)

if __name__ == '__main__':
        main()