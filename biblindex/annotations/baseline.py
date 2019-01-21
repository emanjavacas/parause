
import math
import utils
import random
import numpy as np

random.seed(1001)
np.random.seed(1001)


# take random pick from target document
def random_baseline(at=1, n_background=35000, lemmas=False):
    _, true = utils.load_gold(lemmas=lemmas, return_ids=True)
    true, _ = zip(*true)          # use ids only
    bg = utils.load_background(lemmas=lemmas, return_ids=True)
    random.shuffle(bg)
    bg = bg[:n_background]
    print(len(bg))
    if bg:
        bg, _ = zip(*bg)
    bg += true[:]

    bg = np.array(bg)
    correct = 0
    for doc in range(len(true)):
        correct += (true[doc] in bg[np.random.permutation(len(bg))][:at])

    return correct / len(true)


# random_baseline(at=100, n_background=35000) * 100


def get_d_min_freq(s, freqs):
    """
    Modeling the scholars: Detecting intertextuality  through enhanced
    word-level n-gram matching

    distance between the two most infrequent  words  in  each  of  the  two  phrases
    """
    a, b, *_ = sorted(set(s), key=lambda w: freqs[w])
    return abs(s.index(a) - s.index(b))


def get_d_max_dist(s, matching):
    """
    'Evaluating the literary significance of text re-use in Latin poetry'
    (James Gawley, Christopher Forstall, and Neil Coffee)

    d t : the greatest distance between two matching terms in the target
    d s : the greatest distance between two matching terms in the source
    """
    d = 0
    for i in range(len(s)):
        for j in range(i+1, len(s)):
            if s[i] in matching and s[j] in matching:
                d = max(d, abs(i - j))

    return d


def tesserae_score(s1, s2, freqs1, freqs2, method='min_freq'):

    matching = set(s1).intersection(set(s2))
    if len(matching) < 2:
        return 0

    f_t = sum([1 / freqs1[w] for w in matching])
    f_s = sum([1 / freqs2[w] for w in matching])
    if method == 'min_freq':
        d_t, d_s = get_d_min_freq(s1, freqs1), get_d_min_freq(s2, freqs2)
    elif method == 'max_dist':
        d_t, d_s = get_d_max_dist(s1, matching), get_d_max_dist(s2, matching)

    return math.log((f_t + f_s) / (d_t + d_s))


def tesserae_baseline(src, trg, src_freqs, trg_freqs, at=1, method='min_freq'):
    scores = []
    output = []
    for idx, s1 in enumerate(src):
        tscores = [tesserae_score(s1, s2, src_freqs, trg_freqs) for s2 in trg]
        idxs = np.argsort(tscores)[::-1][:at]
        # filter out those with 0 score
        idxs = [idx for idx in idxs if tscores[idx] > 0]
        output.append(([(idx, tscores[idx], len(set(s1).intersection(set(trg[idx]))))
                        for idx in idxs]))
        scores.append(1 if idx in idxs else 0)

    return sum(scores) / len(scores), output


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--lemmas', action='store_true')
    parser.add_argument('--n_background', default=35000, type=int)
    args = parser.parse_args()

    src, trg = utils.load_gold(lemmas=args.lemmas)
    bg = utils.load_background(lemmas=args.lemmas)
    random.shuffle(bg)
    trg += bg[:args.n_background]
    src_freqs = utils.load_bernard_freqs(lemmas=args.lemmas)
    trg_freqs = utils.get_freqs(trg)

    ats = [1, 5, 10, 20, 50]
    outputpath = 'tesserae.{}'.format(args.n_background)
    if args.lemmas:
        outputpath += '.lemmas'
    outputpath += '.csv'

    with open(outputpath, 'w') as f:
        f.write('\t'.join(['method'] + list(map(str, ats))) + '\n')
        for method in ['max_dist', 'min_freq']:
            scores = []
            for at in ats:
                score, _ = tesserae_baseline(
                    src, trg, src_freqs, trg_freqs, at=at, method=method)
                scores.append(str(score))
            f.write('\t'.join([method] + scores) + '\n')
