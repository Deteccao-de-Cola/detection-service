from datetime import datetime


def _avg_diff_minutes(user_aplicacoes: list, compared_aplicacoes: list) -> float | None:
    diffs = []
    for ua in (user_aplicacoes or []):
        ca = next((c for c in (compared_aplicacoes or []) if c['tipoProva'] == ua['tipoProva']), None)
        if not ca:
            continue
        try:
            t1 = datetime.fromisoformat(ua['dataHoraFim'])
            t2 = datetime.fromisoformat(ca['dataHoraFim'])
            diffs.append(abs((t1 - t2).total_seconds()) / 60)
        except Exception:
            continue
    return sum(diffs) / len(diffs) if diffs else None


def _to_minutes_of_day(iso: str) -> float | None:
    try:
        d = datetime.fromisoformat(iso)
        return d.hour * 60 + d.minute + d.second / 60
    except Exception:
        return None


class AnalyticsService:

    @staticmethod
    def compute_chart_data(comparison_matrix: list) -> dict:
        scatter_points = []

        for comp in comparison_matrix:
            avg_diff = _avg_diff_minutes(comp.get('user_aplicacoes'), comp.get('compared_aplicacoes'))
            if avg_diff is None:
                continue

            jaccard = comp.get('jaccard_index') or 0

            scatter_points.append({
                'user': comp['user'],
                'compared_with': comp['compared_with'],
                'jaccard_index': jaccard,
                'avg_diff': round(avg_diff, 2)
            })

        avg_all = (
            round(sum(p['avg_diff'] for p in scatter_points) / len(scatter_points), 2)
            if scatter_points else 0
        )

        # suspicion table — top 30 by max jaccard
        user_map = {}
        for comp in comparison_matrix:
            jaccard = comp.get('jaccard_index') or 0
            for uid, aplicacoes in [(comp['user'], comp.get('user_aplicacoes')), (comp['compared_with'], comp.get('compared_aplicacoes'))]:
                other_id = comp['compared_with'] if uid == comp['user'] else comp['user']
                if uid not in user_map:
                    user_map[uid] = {'max_jaccard': 0, 'pairs': 0, 'pair_ids': [], 'modules': set(), 'delivery_times': {}}
                entry = user_map[uid]
                entry['max_jaccard'] = max(entry['max_jaccard'], jaccard)
                if jaccard > 0.98:
                    entry['pairs'] += 1
                    entry['pair_ids'].append({'id': other_id, 'jaccard': round(jaccard, 4)})
                for a in (aplicacoes or []):
                    entry['modules'].add(a['tipoProva'])
                    try:
                        entry['delivery_times'][a['tipoProva']] = datetime.fromisoformat(a['dataHoraFim']).strftime('%d/%m %H:%M')
                    except Exception:
                        pass

        suspicion_table = sorted(
            [
                {
                    'user_id': uid,
                    'max_jaccard': round(d['max_jaccard'], 4),
                    'suspicious_pairs': d['pairs'],
                    'suspicious_pair_ids': d['pair_ids'],
                    'modules': list(d['modules']),
                    'delivery_times': d['delivery_times']
                }
                for uid, d in user_map.items()
            ],
            key=lambda x: x['max_jaccard'],
            reverse=True
        )[:30]

        # delivery vs class average — suspects with jaccard >= 0.98
        class_module_times: dict[str, list] = {}
        user_module_times: dict[int, dict] = {}

        for comp in comparison_matrix:
            for uid, aplicacoes in [(comp['user'], comp.get('user_aplicacoes')), (comp['compared_with'], comp.get('compared_aplicacoes'))]:
                if uid not in user_module_times:
                    user_module_times[uid] = {}
                for a in (aplicacoes or []):
                    t = _to_minutes_of_day(a['dataHoraFim'])
                    if t is None:
                        continue
                    mod = a['tipoProva']
                    class_module_times.setdefault(mod, []).append(t)
                    user_module_times[uid][mod] = t

        avg_per_module = {mod: sum(times) / len(times) for mod, times in class_module_times.items()}

        suspect_ids = set()
        for comp in comparison_matrix:
            if (comp.get('jaccard_index') or 0) >= 0.98:
                suspect_ids.add(comp['user'])
                suspect_ids.add(comp['compared_with'])

        delivery_vs_avg = []
        for uid in suspect_ids:
            deviations = {}
            for mod, avg in avg_per_module.items():
                t = user_module_times.get(uid, {}).get(mod)
                if t is not None:
                    deviations[mod] = round(t - avg, 1)
            if deviations:
                delivery_vs_avg.append({'user_id': uid, 'deviations': deviations})

        delivery_vs_avg.sort(key=lambda x: x['user_id'])

        return {
            'scatter_delivery_jaccard': scatter_points,
            'avg_delivery_all_pairs': avg_all,
            'suspicion_table': suspicion_table,
            'delivery_vs_avg': delivery_vs_avg,
        }
