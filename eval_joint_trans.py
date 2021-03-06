# -*- coding: utf-8 -*-
"""
@author: mwahdan
"""

from readers.goo_format_reader import Reader
from vectorizers.trans_vectorizer import TransVectorizer
from models.trans_auto_model import load_joint_trans_model
from utils import flatten

import argparse
import os
import pickle
import tensorflow as tf
from sklearn import metrics
from seqeval.metrics import classification_report, f1_score


# read command-line parameters
parser = argparse.ArgumentParser('Evaluating the Joint Transformer NLU model')
parser.add_argument('--model', '-m', help = 'Path to joint BERT / ALBERT NLU model', type = str, required = True)
parser.add_argument('--data', '-d', help = 'Path to data in Goo et al format', type = str, required = True)
parser.add_argument('--batch', '-bs', help = 'Batch size', type = int, default = 128, required = False)


VALID_TYPES = ['bert', 'albert']

args = parser.parse_args()
load_folder_path = args.model
data_folder_path = args.data
batch_size = args.batch

max_length = 128 # not supported yet   


# loading models
print('Loading models ...')
if not os.path.exists(load_folder_path):
    print('Folder `%s` not exist' % load_folder_path)

with open(os.path.join(load_folder_path, 'tags_vectorizer.pkl'), 'rb') as handle:
    tags_vectorizer = pickle.load(handle)
    slots_num = len(tags_vectorizer.label_encoder.classes_)
with open(os.path.join(load_folder_path, 'intents_label_encoder.pkl'), 'rb') as handle:
    intents_label_encoder = pickle.load(handle)
    intents_num = len(intents_label_encoder.classes_)
    
# loading joint trans model
model = load_joint_trans_model(load_folder_path)

# loading trans vectorizer
pretrained_model_name_or_path = model.model_params['pretrained_model_name_or_path']
cache_dir = model.model_params['cache_dir']
trans_vectorizer = TransVectorizer(pretrained_model_name_or_path, max_length, cache_dir)

data_text_arr, data_tags_arr, data_intents = Reader.read(data_folder_path)
data_input_ids, data_input_mask, data_segment_ids, data_valid_positions, data_sequence_lengths = trans_vectorizer.transform(data_text_arr)

def get_results(input_ids, input_mask, segment_ids, valid_positions, sequence_lengths, tags_arr, 
                intents, tags_vectorizer, intents_label_encoder):
    predicted_tags, predicted_intents = model.predict_slots_intent(
            [input_ids, input_mask, segment_ids, valid_positions], 
            tags_vectorizer, intents_label_encoder, remove_start_end=True)
    gold_tags = [x.split() for x in tags_arr]
    #print(metrics.classification_report(flatten(gold_tags), flatten(predicted_tags), digits=3))
    token_f1_score = metrics.f1_score(flatten(gold_tags), flatten(predicted_tags), average='micro')
    acc = metrics.accuracy_score(intents, predicted_intents)
        
    report = classification_report(gold_tags, predicted_tags, digits=4)
    tag_f1_score = f1_score(gold_tags, predicted_tags, average='micro')
    
    return token_f1_score, tag_f1_score, report, acc

print('==== Evaluation ====')
token_f1_score, tag_f1_score, report, acc = get_results(data_input_ids, data_input_mask, data_segment_ids, data_valid_positions,
                            data_sequence_lengths, 
                            data_tags_arr, data_intents, tags_vectorizer, intents_label_encoder)
print('Slot Classification Report:', report)
print('Slot token f1_score = %f' % token_f1_score)
print('Slot tag f1_score = %f' % tag_f1_score)
print('Intent accuracy = %f' % acc)

tf.compat.v1.reset_default_graph()