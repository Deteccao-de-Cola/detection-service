from datetime import datetime
from src.models.respostas_lake import RespostasLake
from src.services.damerau_levenshtein_service import DamerauLevenshteinService
from src.services.jaccard_service import JaccardService
from src.services.kmeans_levenshtein_service import KMeansLevenshteinService


class ComparisonService:
    # pylint: disable=no-method-argument,redefined-outer-name,reimported,import-outside-toplevel
    @staticmethod
    def init_worker():
        from src import app, db
        app.app_context().push()
        db.engine.dispose()

    # pylint: enable=no-method-argument,redefined-outer-name,reimported,import-outside-toplevel
    @staticmethod
    def _build_response_dicts(contest, contest_to_be_compared):
        user1_dict = {item['itemId']: item['respostaUsuario'] for item in contest}
        user2_dict = {item['itemId']: item['respostaUsuario'] for item in contest_to_be_compared}
        all_items = set(user1_dict.keys()) | set(user2_dict.keys())
        return user1_dict, user2_dict, all_items

    @staticmethod
    def compare(contest, contest_to_be_compared, comparasion_function):
        user1_dict, user2_dict, all_items = ComparisonService._build_response_dicts(contest, contest_to_be_compared)

        user1_responses = set()
        user2_responses = set()
        for itemId in all_items:
            user1_responses.add((itemId, user1_dict.get(itemId, None)))
            user2_responses.add((itemId, user2_dict.get(itemId, None)))

        return comparasion_function(user1_responses, user2_responses)

    @staticmethod
    def compare_sorted(contest, contest_to_be_compared, comparasion_function):
        user1_dict, user2_dict, all_items = ComparisonService._build_response_dicts(contest, contest_to_be_compared)

        all_items_sorted = sorted(all_items)
        user1_responses = [(itemId, user1_dict.get(itemId, None)) for itemId in all_items_sorted]
        user2_responses = [(itemId, user2_dict.get(itemId, None)) for itemId in all_items_sorted]

        return comparasion_function(user1_responses, user2_responses)

    @staticmethod
    def compare_by_timestamp(contest, contest_to_be_compared, comparasion_function):
        user1_responses = [
            (item['itemId'], item['respostaUsuario'])
            for item in contest
        ]
        user2_responses = [
            (item['itemId'], item['respostaUsuario'])
            for item in contest_to_be_compared
        ]
        return comparasion_function(user1_responses, user2_responses)

    @staticmethod
    def compute_kmeans_clusters(all_users, exam_id, k=2, max_iter=10, responses_cache=None, with_timestamp=None):
        if with_timestamp is None:
            with_timestamp = RespostasLake.get_salvar_tempo_resposta(exam_id) if exam_id is not None else True
        if responses_cache is None:
            responses_cache = {
                uid: RespostasLake.select_user_questions(uid, exam_id, withTimestamp=with_timestamp)
                for uid in all_users
            }
        return KMeansLevenshteinService.kmeans_hamming(responses_cache, k=k, max_iter=max_iter)

    @staticmethod
    def process_user_batch(user_batch, all_users, exam_id=None, responses_cache=None, with_timestamp=None):

        batch_results = []

        if with_timestamp is None:
            with_timestamp = RespostasLake.get_salvar_tempo_resposta(exam_id) if exam_id is not None else True

        if responses_cache is None:
            responses_cache = {}
            for uid in all_users:
                responses_cache[uid] = RespostasLake.select_user_questions(uid, exam_id, withTimestamp=with_timestamp)

        for user in user_batch:

            current_user_response = responses_cache[user]
            user_1_avg_time = ComparisonService._calc_avg_interval(current_user_response)

            for other_user in all_users:
                if other_user == user:
                    continue

                elif other_user < user:  # skips half of the pairs to avoid duplicates
                    continue

                respostas_other_user = responses_cache[other_user]

                if not abs(len(current_user_response) - len(respostas_other_user)) <= 2:  # pylint: disable=line-too-long
                    continue

                jaccard_result = ComparisonService.compare(current_user_response,
                                                           respostas_other_user,
                                                           JaccardService.jaccard_index)

                lev_result = ComparisonService.compare(current_user_response,
                                                       respostas_other_user,
                                                       KMeansLevenshteinService.hamming_similarity)

                if with_timestamp:
                    dl_result = ComparisonService.compare_by_timestamp(current_user_response,
                                                            respostas_other_user,
                                                            DamerauLevenshteinService.damerau_levenshtein_similarity_any_swap)  # pylint: disable=line-too-long
                else:
                    dl_result = ComparisonService.compare_sorted(current_user_response,
                                                            respostas_other_user,
                                                            DamerauLevenshteinService.damerau_levenshtein_similarity_any_swap)  # pylint: disable=line-too-long

                result = {
                    'user': user,
                    'compared_with': other_user,
                    'response_other': respostas_other_user,
                    'user_resp': current_user_response,
                    'time_result_diff': ComparisonService._calc_time_diff(
                        current_user_response, respostas_other_user),
                    'user_1_avarage_time': user_1_avg_time,
                    'user_2_avarage_time': ComparisonService._calc_avg_interval(
                        respostas_other_user),
                }

                result['jaccard_index'] = jaccard_result
                result['dl_similarity'], result['dl_operations'] = dl_result
                result['lev_similarity'] = lev_result

                batch_results.append(result)

        return batch_results

    @staticmethod
    def _to_timestamp(t):
        if t is None:
            return None
        if isinstance(t, datetime):
            return t.timestamp()
        try:
            return datetime.strptime(str(t), '%Y-%m-%d %H:%M:%S').timestamp()
        except ValueError:
            return None

    @staticmethod
    def _calc_time_diff(user_resp, response_other):
        user_times = {item['itemId']: ComparisonService._to_timestamp(item.get('respondidaEm'))
                      for item in user_resp}
        other_times = {item['itemId']: ComparisonService._to_timestamp(item.get('respondidaEm'))
                       for item in response_other}

        diffs = [
            abs(user_times[item_id] - other_times[item_id])
            for item_id in set(user_times) & set(other_times)
            if user_times[item_id] is not None and other_times[item_id] is not None
        ]
        return round(sum(diffs) / len(diffs)) if diffs else None

    @staticmethod
    def _calc_avg_interval(user_resp):
        timestamps = sorted(filter(None, [
            ComparisonService._to_timestamp(item.get('respondidaEm'))
            for item in user_resp
        ]))
        if len(timestamps) < 2:
            return None
        intervals = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
        return round(sum(intervals) / len(intervals))
