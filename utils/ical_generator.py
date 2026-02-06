"""
iCal (ICS) 파일 생성기
Google Calendar, Apple Calendar 등과 호환되는 이벤트 내보내기
"""

from datetime import datetime
from typing import List, Dict
import os


class ICalGenerator:
    """iCal 파일 생성기"""

    def __init__(self):
        self.events = []

    def add_event(self, title: str, start_time: datetime, end_time: datetime = None,
                  description: str = None, location: str = None, uid: str = None,
                  all_day: bool = False):
        """이벤트 추가"""
        self.events.append({
            'title': title,
            'start': start_time,
            'end': end_time or start_time,
            'description': description or '',
            'location': location or '',
            'uid': uid or f"{datetime.now().timestamp()}@agency-manager",
            'all_day': all_day
        })

    def add_events_from_db(self, events: List[Dict]):
        """데이터베이스 이벤트 추가"""
        for event in events:
            start_time = datetime.fromisoformat(event['start_date'])
            end_time = None

            if event.get('end_date'):
                end_time = datetime.fromisoformat(event['end_date'])
            elif event.get('all_day'):
                end_time = start_time

            self.add_event(
                title=event['title'],
                start_time=start_time,
                end_time=end_time,
                description=event.get('description'),
                location=event.get('location'),
                uid=str(event['id']) if event.get('id') else None,
                all_day=event.get('all_day', True)
            )

    def generate(self) -> str:
        """iCal 콘텐츠 생성"""
        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Agency Manager//Calendar//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
            'X-WR-CALNAME:Agency Manager Calendar',
            'X-WR-TIMEZONE:Asia/Seoul',
            'X-WR-CALDESC:Agency Management System Calendar',
        ]

        for event in self.events:
            lines.extend(self._format_event(event))

        lines.append('END:VCALENDAR')
        return '\r\n'.join(lines)

    def _format_event(self, event: Dict) -> List[str]:
        """이벤트를 iCal 형식으로 변환"""
        lines = ['BEGIN:VEVENT']

        # UID
        lines.append(f'UID:{event["uid"]}')

        # 제목
        lines.append(f'SUMMARY:{self._escape_text(event["title"])}')

        # 설명
        if event['description']:
            lines.append(f'DESCRIPTION:{self._escape_text(event["description"])}')

        # 위치
        if event['location']:
            lines.append(f'LOCATION:{self._escape_text(event["location"])}')

        # 시작/종료 시간
        if event['all_day']:
            # 종일 이벤트
            date_format = '%Y%m%d'
            lines.append(f'DTSTART;VALUE=DATE:{event["start"].strftime(date_format)}')

            # 종료일은 다음 날로 설정 (iCal 표준)
            if event['end'] == event['start']:
                end_date = event['start']
            else:
                end_date = event['end']
            lines.append(f'DTEND;VALUE=DATE:{end_date.strftime(date_format)}')
        else:
            # 시간 지정 이벤트
            datetime_format = '%Y%m%dT%H%M%S'
            lines.append(f'DTSTART:{event["start"].strftime(datetime_format)}')
            lines.append(f'DTEND:{event["end"].strftime(datetime_format)}')

        # 타임스탬프
        lines.append(f'DTSTAMP:{datetime.now().strftime("%Y%m%dT%H%M%SZ")}')

        lines.append('END:VEVENT')
        return lines

    def _escape_text(self, text: str) -> str:
        """iCal 텍스트 이스케이프 처리"""
        if not text:
            return ''

        # 백슬래시, 쉼표, 세미콜론, 개행 이스케이프
        text = text.replace('\\', '\\\\')
        text = text.replace(',', '\\,')
        text = text.replace(';', '\\;')
        text = text.replace('\n', '\\n')
        text = text.replace('\r', '')

        return text

    def save_to_file(self, filepath: str):
        """파일로 저장"""
        content = self.generate()

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    def get_bytes(self) -> bytes:
        """바이트 데이터 반환 (다운로드용)"""
        return self.generate().encode('utf-8')


def generate_ical_from_events(events: List[Dict]) -> bytes:
    """이벤트 리스트로부터 iCal 파일 생성 (편의 함수)"""
    generator = ICalGenerator()
    generator.add_events_from_db(events)
    return generator.get_bytes()


def generate_google_calendar_url(events: List[Dict]) -> str:
    """Google Calendar 일괄 추가 URL 생성

    참고: Google Calendar는 웹 인터페이스에서 한 번에 하나의 이벤트만 추가 가능
    여러 이벤트는 iCal 파일로 내보내기 필요
    """
    if not events:
        return "https://calendar.google.com/calendar"

    event = events[0]
    start = datetime.fromisoformat(event['start_date'])

    base_url = "https://calendar.google.com/calendar/render"
    params = {
        'action': 'TEMPLATE',
        'text': event['title'],
        'dates': f"{start.strftime('%Y%m%dT%H%M%S')}/{start.strftime('%Y%m%dT%H%M%S')}",
    }

    if event.get('description'):
        params['details'] = event['description']

    if event.get('location'):
        params['location'] = event['location']

    query_string = '&'.join(f"{k}={v}" for k, v in params.items())
    return f"{base_url}?{query_string}"
