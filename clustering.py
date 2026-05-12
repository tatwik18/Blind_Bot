"""
Student Learning Pattern Clustering
Groups students by behavioral features extracted from their session history
using a pure-Python K-means implementation (no external ML dependencies).
"""

import re
import math

_TOPIC_KEYWORDS = {
    'tenses': [
        'was', 'were', 'will', 'would', 'had', 'has', 'have',
        'past', 'future', 'present', 'tense', 'tha', 'thi', 'hoga',
    ],
    'vocabulary': [
        'matlab', 'meaning', 'word', 'shabd', 'bolte', 'kehte',
        'iska', 'arth', 'kya kehte', 'new word',
    ],
    'pronunciation': [
        'bolna', 'pronunciation', 'kaise bolta', 'kaise bolte',
        'ucharan', 'pronounce', 'bol do',
    ],
    'grammar': [
        'grammar', 'sentence', 'plural', 'singular', 'noun', 'verb',
        'adjective', 'pronoun', 'preposition', 'tense',
    ],
    'conversation': [
        'please', 'thank', 'sorry', 'excuse', 'hello',
        'good morning', 'how are you', 'my name',
    ],
}

_CLUSTER_COLORS = ['#56d364', '#79c0ff', '#f78166', '#e3b341', '#bc8cff']


# ── Feature extraction ────────────────────────────────────────────────────────

def _extract_features(record):
    """
    Build a normalised feature dict for one student.
    Returns None when the student has fewer than 2 user messages.
    """
    # Support both new sessions dict and legacy last_session flat list
    sessions = record.get('sessions', {})
    if sessions:
        # Combine all messages across all days for clustering
        session = [msg for day_msgs in sessions.values() for msg in day_msgs]
    else:
        session = record.get('last_session', [])
    user_msgs = [
        t['content'] for t in session
        if t.get('role') == 'user' and t.get('content', '').strip()
    ]
    if len(user_msgs) < 2:
        return None

    joined      = ' '.join(user_msgs).lower()
    total_words = sum(len(m.split()) for m in user_msgs)
    all_words   = re.findall(r'\b[a-zA-Z]+\b', joined)

    features = {
        # normalise avg message length to ~0-1 (cap at 15 words)
        'avg_msg_len':    min(total_words / len(user_msgs) / 15.0, 1.0),
        'vocab_richness': len(set(all_words)) / max(len(all_words), 1),
        'question_rate':  sum(
            1 for m in user_msgs
            if '?' in m or re.search(r'\bkya\b|\bhow\b|\bwhat\b|\bwhy\b', m.lower())
        ) / len(user_msgs),
        'msg_count_norm': min(len(user_msgs) / 20.0, 1.0),
    }

    for topic, kws in _TOPIC_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in joined)
        features[f'topic_{topic}'] = min(hits / max(len(kws), 1), 1.0)

    return features


# ── Pure-Python K-means ───────────────────────────────────────────────────────

def _dist(a, b, keys):
    return math.sqrt(sum((a.get(k, 0) - b.get(k, 0)) ** 2 for k in keys))


def _centroid(points, keys):
    return {k: sum(p.get(k, 0) for p in points) / len(points) for k in keys}


def _kmeans(feature_list, k, max_iter=30):
    if not feature_list:
        return []
    k        = min(k, len(feature_list))
    keys     = list(feature_list[0].keys())
    centroids = [dict(feature_list[i]) for i in range(k)]
    labels   = [0] * len(feature_list)

    for _ in range(max_iter):
        new_labels = [
            min(range(k), key=lambda ci, f=f: _dist(f, centroids[ci], keys))
            for f in feature_list
        ]
        if new_labels == labels:
            break
        labels = new_labels
        for ci in range(k):
            pts = [feature_list[i] for i, lbl in enumerate(labels) if lbl == ci]
            if pts:
                centroids[ci] = _centroid(pts, keys)

    return labels


# ── Cluster description ───────────────────────────────────────────────────────

def _describe_cluster(features_list):
    if not features_list:
        return "No data"
    n       = len(features_list)
    avg_len = sum(f['avg_msg_len'] for f in features_list) / n * 15  # denormalise

    topics      = ['tenses', 'vocabulary', 'pronunciation', 'grammar', 'conversation']
    topic_scores = {
        t: sum(f.get(f'topic_{t}', 0) for f in features_list) / n
        for t in topics
    }
    top_topic = max(topic_scores, key=topic_scores.get)

    if avg_len < 3:
        style = "Short-answer learners"
    elif avg_len < 6:
        style = "Conversational learners"
    else:
        style = "Engaged / verbose learners"

    topic_desc = {
        'tenses':        'struggling with tenses',
        'vocabulary':    'focused on vocabulary building',
        'pronunciation': 'working on pronunciation',
        'grammar':       'exploring grammar concepts',
        'conversation':  'practicing daily conversation',
    }
    return f"{style} — {topic_desc.get(top_topic, top_topic)}"


# ── Public API ────────────────────────────────────────────────────────────────

def cluster_students(students_db, k=3):
    """
    Group students by learning behaviour.

    Args:
        students_db: the full dict loaded from students.json
        k: number of clusters (capped at number of eligible students)

    Returns:
        List of cluster dicts:
            { id, color, description, size, students: [{id, name}] }
        Returns [] when fewer than 2 students have usable session data.
    """
    eligible = []
    for sid, record in students_db.items():
        if not isinstance(record, dict) or 'name' not in record:
            continue
        feats = _extract_features(record)
        if feats is not None:
            eligible.append((sid, record['name'], feats))

    if len(eligible) < 2:
        return []

    feature_list = [e[2] for e in eligible]
    labels       = _kmeans(feature_list, k=min(k, len(eligible)))

    groups = {}
    for i, (sid, name, feats) in enumerate(eligible):
        lbl = labels[i]
        if lbl not in groups:
            groups[lbl] = {'students': [], 'features': []}
        groups[lbl]['students'].append({'id': sid, 'name': name})
        groups[lbl]['features'].append(feats)

    result = []
    for ci, (_, data) in enumerate(groups.items()):
        result.append({
            'id':          ci + 1,
            'color':       _CLUSTER_COLORS[ci % len(_CLUSTER_COLORS)],
            'description': _describe_cluster(data['features']),
            'students':    data['students'],
            'size':        len(data['students']),
        })
    return result
