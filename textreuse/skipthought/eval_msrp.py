
import os
import tqdm
import numpy as np
from sklearn.model_selection import KFold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, accuracy_score, confusion_matrix

import seqmod.utils as u

from textreuse.skipthought.model import SkipThoughts, Loss


def encode_dataset(model, A, B, labels, use_feats, use_norm=True):
    """
    Encode pairs to output features
    """
    enc1, enc2 = model.encode(A, use_norm=use_norm), model.encode(B, use_norm=use_norm)
    feats = np.concatenate([np.abs(enc1 - enc2), enc1 * enc2], axis=1)

    if use_feats:
        feats = np.concatenate([feats, count_feats(A, B)], axis=1)

    # if use_feats: # normalize count feature to -1, 1 range
    #     feats[:, -6:] = MinMaxScaler(feature_range=(-1, 1)).fit_transform(feats[:, -6:])

    return feats, np.array(labels, dtype=np.float)


def count_feats(A, B):
    """
    Compute easy set overlap features.
    (https://github.com/ryankiros/skip-thoughts/blob/master/eval_msrp.py)
    """

    def is_number(w):
        try:
            float(w)
            return True
        except ValueError:
            return False

    features = np.zeros((len(A), 6))

    for i, (tA, tB) in enumerate(zip(A, B)):

        nA = [w for w in tA if is_number(w)]
        nB = [w for w in tB if is_number(w)]

        if set(nA) == set(nB):
            features[i,0] = 1.
    
        if set(nA) == set(nB) and len(nA) > 0:
            features[i,1] = 1.
    
        if set(nA) <= set(nB) or set(nB) <= set(nA): 
            features[i,2] = 1.
    
        features[i,3] = len(set(tA) & set(tB)) / len(set(tA))
        features[i,4] = len(set(tA) & set(tB)) / len(set(tB))
        features[i,5] = 0.5 * ((len(tA) / len(tB)) + (len(tB) / len(tA)))

    return features


def eval_kfold(feats, labels, k=10, shuffle=True):
    kf = KFold(n_splits=k, shuffle=shuffle)
    Cs = [2 ** C for C in range(5)]  # try values
    scores = []

    for C in Cs:
        run_scores = []

        for train, test in kf.split(feats):
            clf = LogisticRegression(C=C).fit(feats[train], labels[train])
            y_hat, y_true = clf.predict(feats[test]), labels[test]
            run_scores.append(f1_score(y_true, y_hat))

        print("C={}; f1={:.4f} (+= {:.4f})".format(
            C, np.mean(run_scores), np.std(run_scores)))

        scores.append(np.mean(run_scores))

    best_C = Cs[np.argmax(scores)]

    return best_C


def evaluate(train_X, train_y, test_X, test_y, use_kfold=False, k=10):
    C = 4 if not use_kfold else eval_kfold(train_X, train_y, k=k)
    clf = LogisticRegression(C=C).fit(train_X, train_y)
    preds = clf.predict(test_X)

    print("Confusion matrix:\n{}".format(str(confusion_matrix(test_y, preds))))
    print("Best C: {}".format(C))

    f1, acc = f1_score(test_y, preds), accuracy_score(test_y, preds)
    print("F1-score: {:g}".format(p))
    print("Accuracy: {:g}".format(mse))

    return f1, acc, C
    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model')
    parser.add_argument('--use_kfold', action='store_true')
    parser.add_argument('--use_feats', action='store_true')
    parser.add_argument('--use_norm', action='store_true')
    parser.add_argument('--batch_size', default=50, type=int)
    parser.add_argument('--embeddings',
                        default='/home/corpora/word_embeddings/fasttext.wiki.en.bin')
    parser.add_argument('--gpu', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    from textreuse.datasets import default_pairs, PATHS
    import utils

    model = u.load_model(args.model)
    model.eval()

    # expand
    targets = utils.get_targets(
        model.encoder.embeddings.d.vocab,
        default_pairs(PATHS['MSRP']['train']), default_pairs(PATHS['test']))
    model.encoder.embeddings.expand_space(
        args.embeddings,
        targets=targets, words=targets + model.encoder.embeddings.d.vocab)

    if args.gpu:
        model.cuda()

    # train
    X, y = zip(*list(default_pairs(PATHS['MSRP']['train'])))
    (A, B) = zip(*X)
    train_X, train_y = encode_dataset(
        model, A, B, y, use_feats=args.use_feats, use_norm=args.use_norm)

    # test
    X, y = zip(*list(default_pairs(PATHS['MSRP']['test'])))
    (A, B) = zip(*X)
    test_X, test_y = encode_dataset(
        model, A, B, y, use_feats=args.use_feats, use_norm=args.use_norm)

    f1, acc, C = evaluate(train_X, train_y, test_X, test_y, use_kfold=args.use_kfold)
    with open(os.path.join(os.path.dirname(args.model), 'msrp.csv'), 'a') as f:
        formatter = "\nModel: {}\tF1: {:g}\tAcc: {:g}\tC: {:g}\tfeats: {}" + \
                    "\tNorm: {}\tEmbs: {}"
        f.write(formatter.format(os.path.basename(args.model), f1, acc, C,
                                 str(args.use_feats), str(args.use_norm),
                                 os.path.basename(args.embeddings)))
