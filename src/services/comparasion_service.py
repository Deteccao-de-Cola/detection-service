from datetime import datetime
from src.models.respostas_lake import RespostasLake
from src.services.damerau_levenshtein_service import DamerauLevenshteinService
from src.services.jaccard_service import JaccardService


class ComparisonService:
    # pylint: disable=no-method-argument,redefined-outer-name,reimported,import-outside-toplevel
    @staticmethod
    def init_worker():
        from src import app, db
        app.app_context().push()
        db.engine.dispose()

    # pylint: enable=no-method-argument,redefined-outer-name,reimported,import-outside-toplevel
    @staticmethod
    def compare(contest, contest_to_be_compared, comparasion_function):
        user1_dict = {item['itemId']: item['respostaUsuario'] for item in contest}
        user2_dict = {item['itemId']: item['respostaUsuario'] for item in contest_to_be_compared}

        all_items = set(user1_dict.keys()) | set(user2_dict.keys())

        user1_responses = set()
        user2_responses = set()
        for itemId in all_items:
            resp1 = user1_dict.get(itemId, None)
            user1_responses.add((itemId, resp1))

            resp2 = user2_dict.get(itemId, None)
            user2_responses.add((itemId, resp2))

        return comparasion_function(user1_responses, user2_responses)

    @staticmethod
    def process_user_batch(user_batch, all_users, exam_id=None, metrics='both'):

        batch_results = []

        for user in user_batch:

            current_user_response = RespostasLake.select_user_questions(user, exam_id)
            for other_user in all_users:
                if other_user == user:
                    continue

                respostas_other_user = RespostasLake.select_user_questions(other_user, exam_id)
                jaccard_result = None
                dl_result = None
                # {item['itemId']: item['respostaUsuario'] for item in contest}

                if metrics in ['jaccard', 'both']:
                    jaccard_result = ComparisonService.compare(current_user_response,
                                                                respostas_other_user,
                                                                JaccardService.jaccard_index)

                if metrics in ['dl', 'both']:
                    dl_result = ComparisonService.compare(current_user_response,
                                                            respostas_other_user,
                                                            DamerauLevenshteinService.damerau_levenshtein_similarity)  # pylint: disable=line-too-long

                time_result = ComparisonService.compare_time(current_user_response, respostas_other_user)  # pylint: disable=line-too-long
                user_1_avarage_time = ComparisonService.avg_response_time(current_user_response)  # pylint: disable=line-too-long
                user_2_avarage_time = ComparisonService.avg_response_time(respostas_other_user)  # pylint: disable=line-too-long

                # should_append = False
                # if metrics == 'jaccard' and jaccard_result and jaccard_result > 0.01:
                #     should_append = True
                # elif metrics == 'dl' and dl_result and dl_result > 0.01:
                #     should_append = True
                # elif metrics == 'both' and jaccard_result and jaccard_result > 0.01:
                #     should_append = True

                # if should_append:
                result = {
                    'user': user,
                    'compared_with': other_user,
                    'response_other': respostas_other_user,
                    'user_resp': current_user_response,
                    'time_result': time_result,
                    'user_1_avarage_time': user_1_avarage_time,
                    'user_2_avarage_time': user_2_avarage_time
                }

                if jaccard_result is not None:
                    result['jaccard_index'] = jaccard_result
                if dl_result is not None:
                    result['dl_similarity'] = dl_result
                if time_result is not None:
                    result['time_result'] = time_result
                if user_1_avarage_time is not None:
                    result['user_1_avarage_time'] = user_1_avarage_time
                if user_2_avarage_time is not None:
                    result['user_2_avarage_time'] = user_2_avarage_time

                batch_results.append(result)

        return batch_results

    @staticmethod
    def compare_time(user1_responses, user2_responses):
        from datetime import datetime

        user1_times = {item['itemId']: item['respondidaEm'] for item in user1_responses}
        user2_times = {item['itemId']: item['respondidaEm'] for item in user2_responses}

        common_items = set(user1_times.keys()) & set(user2_times.keys())

        if not common_items:
            return None

        time_diffs = []
        for item_id in common_items:
            t1 = user1_times[item_id]
            t2 = user2_times[item_id]

            if isinstance(t1, str):
                t1 = datetime.fromisoformat(t1)
            if isinstance(t2, str):
                t2 = datetime.fromisoformat(t2)

            diff = abs((t1 - t2).total_seconds())
            time_diffs.append(diff)

        return sum(time_diffs) / len(time_diffs)

    @staticmethod
    def avg_response_time(user_responses):
        times = sorted(item['respondidaEm'] for item in user_responses)

        if len(times) < 2:
            return None

        intervals = []
        for i in range(1, len(times)):
            diff = (times[i] - times[i - 1]).total_seconds()
            intervals.append(diff)

        return sum(intervals) / len(intervals)
