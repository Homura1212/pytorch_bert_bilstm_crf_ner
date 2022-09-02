import os
import numpy as np
import torch
import json
from utils import commonUtils, metricsUtils, decodeUtils, trainUtils
import bert_ner_model
from transformers import BertTokenizer


def predict(raw_text, model, device, args, id2query):
    model = model.to(device)
    model.eval()
    with torch.no_grad():
        tokenizer = BertTokenizer(
            os.path.join(args.bert_dir, 'vocab.txt'))
        # tokens = commonUtils.fine_grade_tokenize(raw_text, tokenizer)
        tokens = [i for i in raw_text]
        encode_dict = tokenizer.encode_plus(text=tokens,
                                            max_length=args.max_seq_len,
                                            padding='max_length',
                                            truncation='longest_first',
                                            is_pretokenized=True,
                                            return_token_type_ids=True,
                                            return_attention_mask=True)
        # tokens = ['[CLS]'] + tokens + ['[SEP]']
        token_ids = torch.from_numpy(np.array(encode_dict['input_ids'])).unsqueeze(0).to(device)
        attention_masks = torch.from_numpy(np.array(encode_dict['attention_mask'], dtype=np.uint8)).unsqueeze(0).to(
            device)
        token_type_ids = torch.from_numpy(np.array(encode_dict['token_type_ids'])).unsqueeze(0).to(device)
        logits = model(token_ids.to(device), attention_masks.to(device), token_type_ids.to(device), None)
        if args.use_crf == 'True':
            output = logits
        else:
            output = logits.detach().cpu().numpy()
            output = np.argmax(output, axis=2)
        pred_entities = decodeUtils.bioes_decode(output[0][1:1 + len(tokens)], "".join(tokens), id2query)
        # print(pred_entities)
        return pred_entities


if __name__ == "__main__":
    args_path = "checkpoints/bert_crf_cner/args.json"

    with open(args_path, "r", encoding="utf-8") as fp:
        tmp_args = json.load(fp)


    class Dict2Class:
        def __init__(self, **entries):
            self.__dict__.update(entries)


    args = Dict2Class(**tmp_args)
    args.gpu_ids = "0" if torch.cuda.is_available() else "-1"
    print(args.__dict__)

    other_path = os.path.join(args.data_dir, 'mid_data')
    ent2id_dict = commonUtils.read_json(other_path, 'nor_ent2id')
    query2id = {}
    id2query = {}
    for k, v in ent2id_dict.items():
        query2id[k] = v
        id2query[v] = k

    raw_text = "虞兔良先生：1963年12月出生，汉族，中国国籍，无境外永久居留权，浙江绍兴人，中共党员，MBA，经济师。"
    print(raw_text)
    model_name = args.model_name
    model_path = './checkpoints/{}_{}/model.pt'.format(model_name, args.data_name)
    model = bert_ner_model.BertNerModel(args)
    model, device = trainUtils.load_model_and_parallel(model, args.gpu_ids, model_path)
    print(predict(raw_text, model, device, args, id2query))
