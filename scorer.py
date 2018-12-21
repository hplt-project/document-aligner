
import math
import sys
import time
from collections import Counter
from functools import partial

from nltk.tokenize import wordpunct_tokenize
from numpy import float32, isnan
from scipy.sparse import vstack as sp_vstack
from scipy.sparse import csr_matrix, lil_matrix
from sklearn.metrics.pairwise import pairwise_distances


def _ngram_helper(words, n, hash_values):
    words = [w.strip() for w in words if w.strip()]
    ngrams = (" ".join(words[i:i + n]) for i in
              range(max(len(words) - n + 1, 1)))
    ngrams = [ng for ng in ngrams if ng.strip()]
    if hash_values:
        return map(hash, ngrams)
    return ngrams


def english_ngrams_from_text(n, hash_values, ignore_set, page):
    words = wordpunct_tokenize(page)
    ngrams = _ngram_helper(words, n, hash_values)

    if ignore_set:
        return [ng for ng in ngrams if ng not in ignore_set]

    return ngrams


class ExtractionMapper(object):

    def __init__(self, extraction_function=None):
        self.ef = extraction_function

    def extract(self, corpus, pool=None):
        if pool is not None:
            return pool.map(self.ef, corpus)
        return map(self.ef, corpus)

    def extract_single(self, page):
        return self.ef(page)

    def extract_source(self, corpus):
        return self.extract(corpus)

    def extract_target(self, corpus):
        return self.extract(corpus)


class EnglishWordExtractor(ExtractionMapper):

    def __init__(self, n=1, hash_values=False, ignore_set=None):
        super(EnglishWordExtractor, self).__init__(
            extraction_function=partial(english_ngrams_from_text,
                                        n, hash_values, ignore_set))


class DocumentVectorExtractor(object):

    def __init__(self, extraction_mapper,
                 min_count=1, max_count=1000,
                 smooth=0, lda_dim=0):
        self.min_term_count = min_count
        self.max_term_count = max_count
        self.ef = extraction_mapper
        self.tf_smooth = smooth // 6
        self.idf_smooth = smooth % 6
        sys.stderr.write("TF: {0}\nIDF: {1}\n".format(
            self.tf_smooth, self.idf_smooth))
        assert int(self.tf_smooth) in range(7)
        assert int(self.idf_smooth) in range(6)
        self.lda_dim = lda_dim

    def estimate_idf(self, source_corpus, target_corpus):
        counts = Counter()
        self.ndocs = 0
        for items in list(map(self.ef.extract_single, source_corpus)):
            counts.update(set(items))
            self.ndocs += 1
        for items in list(map(self.ef.extract_single, target_corpus)):
            counts.update(set(items))
            self.ndocs += 1

        self.term2idf = {}
        self.term2idx = {}
        self.ignored_terms = set()
        self.max_count = max(counts.values())
        for term, docs_with_term in counts.items():
            docs_with_term = float(docs_with_term)
            if int(docs_with_term) < self.min_term_count:
                self.ignored_terms.add(term)
                continue

            if int(docs_with_term) > self.max_term_count:
                self.ignored_terms.add(term)
                continue

            idf = 1
            if self.idf_smooth == 0:
                idf = 1
            elif self.idf_smooth == 1:
                idf = math.log(self.ndocs / docs_with_term)
            elif self.idf_smooth == 2:
                idf = math.log(1 + self.ndocs / docs_with_term)
            elif self.idf_smooth == 3:
                idf = math.log(1 + self.max_count / docs_with_term)
            elif self.idf_smooth == 4:
                if self.ndocs > docs_with_term:
                    idf = math.log(
                        (self.ndocs - docs_with_term) / docs_with_term)
                else:
                    idf = 0
            elif self.idf_smooth == 5:
                idf = 1 + math.log(self.ndocs / (docs_with_term + 1))

            self.term2idf[term] = idf
            self.term2idx[term] = len(self.term2idx)

        sys.stderr.write("{0} terms, {1} ignored\n".format(
            len(self.term2idx), len(self.ignored_terms)))

    def extract(self, corpus):
        m = lil_matrix((len(corpus), len(self.term2idx)), dtype=float32)
        for doc_idx, page in enumerate(corpus):
            counts = Counter(self.ef.extract_single(page))
            if not counts:
                continue
            local_max_count = float(max(counts.values()))
            local_sum = float(sum(counts.values()))
            for ngram, count in counts.items():
                if ngram not in self.term2idx:
                    if ngram not in self.ignored_terms:
                        sys.stderr.write("unknown ngram: %s\n" % (ngram))
                    continue

                idf = self.term2idf[ngram]
                idx = self.term2idx[ngram]

                tf = 1
                if self.tf_smooth == 0:
                    tf = 1
                elif self.tf_smooth == 1:
                    tf = count
                elif self.tf_smooth == 2:
                    tf = 1 + math.log(count)
                elif self.tf_smooth == 3:
                    tf = 0.4 + 0.6 * count / local_max_count
                elif self.tf_smooth == 4:
                    tf = count / local_max_count
                elif self.tf_smooth == 5:
                    tf = count / local_sum
                elif self.tf_smooth == 6:
                    tf = math.sqrt(count)
                tfidf = tf * idf
                m[doc_idx, idx] = tfidf

        m = csr_matrix(m, dtype=float32)
        return m


class CosineDistanceScorer(object):

    def __init__(self, extraction_mapper, min_count, metric='cosine',
                 smooth=0, ignore=None, threshold=0.1, batch_size=10000):
        self.name = "Cosine Distance Scorer"
        self.metric = metric
        self.vector_extractor = DocumentVectorExtractor(
            extraction_mapper=extraction_mapper, min_count=min_count,
            smooth=smooth)
        self.threshold = threshold
        self.batch_size = batch_size

    def batched_pairwise_distances(self, X_csr, Y_csr):

        def get_row_batch(M, batch):
            for cols_step in range(math.ceil(M.shape[0] / batch)):
                yield M[cols_step * batch:(cols_step + 1) * batch]

        all_csr = None
        for idx, X_batch in enumerate(get_row_batch(X_csr, self.batch_size)):
            pd = 1 - pairwise_distances(X_batch, Y_csr,  metric=self.metric)
            pd[(isnan(pd)) | (pd < self.threshold)] = 0

            if all_csr is None:
                all_csr = csr_matrix(pd, dtype=float32)
            else:
                all_csr = sp_vstack((all_csr, csr_matrix(pd, dtype=float32)))

        return all_csr

    def score(self, source_corpus, target_corpus, weighting=None, pool=None):
        start = time.time()
        self.vector_extractor.estimate_idf(source_corpus, target_corpus)
        sys.stderr.write(
            "IDF estimation took {0:.5f} seconds\n".format(time.time() - start))

        start = time.time()
        source_matrix = self.vector_extractor.extract(source_corpus)
        target_matrix = self.vector_extractor.extract(target_corpus)
        sys.stderr.write(
            "Matrix extraction took {0:.5f} seconds\n".format(time.time() - start))

        start = time.time()
        del self.vector_extractor

        if source_matrix.getnnz() == 0 or target_matrix.getnnz() == 0:
            d=None
        else:
            d = self.batched_pairwise_distances(source_matrix, target_matrix)

        sys.stderr.write(
            "Scoring took {0:.5f} seconds\n".format(time.time() - start))
        return d
