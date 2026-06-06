BEGIN;

CREATE OR REPLACE FUNCTION survey.sync_other_pest_event_from_inspection()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
DECLARE
    v_site sites."其他害虫点位基础表"%ROWTYPE;
    v_last_event_type ledger.other_pest_event_type;
    v_event_type ledger.other_pest_event_type;
    v_location_name text;
    v_host_tree text;
    v_detail text;
    v_event_note text;
BEGIN
    SELECT *
    INTO v_site
    FROM sites."其他害虫点位基础表"
    WHERE "编号" = NEW."编号";

    IF NOT FOUND THEN
        RAISE EXCEPTION 'sites."其他害虫点位基础表" 中不存在编号 %，无法建立其他害虫闭环记录', NEW."编号";
    END IF;

    SELECT e."事件类型"
    INTO v_last_event_type
    FROM ledger."2026年其他害虫问题点位事件流水表" e
    WHERE e."编号" = NEW."编号"
      AND e."虫害类型" = NEW."虫害类型"
      AND e."事件时间"::date < NEW."调查日期"
    ORDER BY e."事件时间" DESC, e.id DESC
    LIMIT 1;

    v_location_name := COALESCE(NULLIF(btrim(v_site."点位名称"), ''), '未命名点位');
    v_host_tree := COALESCE(NULLIF(btrim(v_site."寄主树种"), ''), '未登记寄主树种');

    IF v_last_event_type IS NULL THEN
        IF NEW."调查结论" = '发现问题' THEN
            v_event_type := '调查下派';
            v_detail := format(
                '%s%s%s点位发现%s问题，寄主树种为%s，现场情况：%s。',
                COALESCE(v_site."属地", ''),
                v_location_name,
                NEW."编号",
                NEW."虫害类型",
                v_host_tree,
                NEW."详细描述"
            );
        ELSE
            RETURN NEW;
        END IF;
    ELSIF v_last_event_type = '防治' THEN
        IF NEW."调查结论" = '发现问题' THEN
            v_event_type := '复查异常';
            v_detail := format(
                '%s%s%s点位经复查仍发现%s问题，寄主树种为%s，现场情况：%s。',
                COALESCE(v_site."属地", ''),
                v_location_name,
                NEW."编号",
                NEW."虫害类型",
                v_host_tree,
                NEW."详细描述"
            );
        ELSE
            v_event_type := '复查合格';
            v_detail := format(
                '%s%s%s点位经复查未再发现%s问题，寄主树种为%s，现场情况：%s。',
                COALESCE(v_site."属地", ''),
                v_location_name,
                NEW."编号",
                NEW."虫害类型",
                v_host_tree,
                NEW."详细描述"
            );
        END IF;
    ELSE
        RETURN NEW;
    END IF;

    v_event_note := format(
        '来源=survey."其他害虫调查表"；调查日期=%s；原详细描述=%s',
        NEW."调查日期",
        NEW."详细描述"
    );

    INSERT INTO ledger."2026年其他害虫问题点位事件流水表" (
        "事件时间",
        "事件类型",
        "虫害类型",
        "属地",
        "编号",
        "点位名称",
        "寄主树种",
        "本次调查结论",
        "本次详细情况",
        "备注"
    )
    VALUES (
        NEW."调查日期"::timestamp without time zone,
        v_event_type,
        NEW."虫害类型",
        NULLIF(btrim(v_site."属地"), ''),
        NEW."编号",
        NULLIF(btrim(v_site."点位名称"), ''),
        NULLIF(btrim(v_site."寄主树种"), ''),
        NEW."调查结论",
        v_detail,
        v_event_note
    )
    ON CONFLICT ("编号", "虫害类型", "事件类型", "事件时间") DO NOTHING;

    RETURN NEW;
END
$function$;

COMMIT;
