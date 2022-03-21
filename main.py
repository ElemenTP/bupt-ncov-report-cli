import argparse
import datetime
import logging
import signal
import traceback
from logging.handlers import TimedRotatingFileHandler
from shutil import copyfile
from typing import List

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from peewee import SqliteDatabase

from include import *


def get_users_by_seqids(seqids: List[int]):
    available_targets = get_buptusers()
    assert max(seqids) <= len(available_targets), "Seqid out of range."
    return [available_targets[i - 1] for i in seqids]


def get_buptusers(include_all=False):
    if include_all:
        return BUPTUser.select()
    else:
        return BUPTUser.select().where(BUPTUser.status != BUPTUserStatus.removed)


def list():
    print(f"用户列表查询中 ...\n")
    users = get_buptusers()
    ret_msgs = []
    ret_msg = ""
    for i, user in enumerate(users):
        if i % 10 == 0 and i != 0:
            ret_msgs.append(ret_msg)
            ret_msg = ""
        id = i + 1
        ret_msg += f"ID: `{id}`\n"
        if user.username != None:
            ret_msg += (
                f"Username: `{user.username}`\n"  # Password: `{user.password}`\n'
            )
        else:
            ret_msg += f"eai-sess: `{user.cookie_eaisess}`\n"  # UUKey: `{user.cookie_uukey}`\n'
        if user.status == BUPTUserStatus.normal:
            ret_msg += f"自动签到: `启用`\n"
        else:
            ret_msg += f"自动签到: `暂停`\n"
        if user.xisu_checkin_status == BUPTUserStatus.normal:
            ret_msg += f"自动晨午晚检: `启用`\n"
        else:
            ret_msg += f"自动晨午晚检: `暂停`\n"
        if user.latest_response_data == None:
            ret_msg += "从未尝试签到\n"
        else:
            ret_msg += f"最后签到时间: `{user.latest_response_time}`\n"
            ret_msg += f"最后签到返回: `{user.latest_response_data[:100]}`\n"

        if user.latest_xisu_checkin_response_data == None:
            ret_msg += "从未尝试晨午晚检签到\n"
        else:
            ret_msg += f"最后晨午晚检签到时间: `{user.latest_xisu_checkin_response_time}`\n"
            ret_msg += f"最后晨午晚检签到返回: `{user.latest_xisu_checkin_response_data[:100]}`\n"

        ret_msg += f"暂停 pause {id}   恢复 resume {id}\n签到 checkin {id} 删除 remove {id}\n晨午晚检签到 checkinxisu {id}\n"
        ret_msg += f"暂停自动晨午晚检 pausexisu {id} 恢复自动晨午晚检 resumexisu {id}\n"
        ret_msg += "\n"
    ret_msgs.append(ret_msg)

    if len(users) == 0:
        ret_msgs = ["用户列表为空"]
    if len(users) >= 2:
        ret_msgs[
            -1
        ] += f"恢复全部 resume  暂停全部 pause\n签到全部 checkin  删除全部 remove all \n晨午晚检签到 checkinxisu\n暂停自动晨午晚检 pausexisu 恢复自动晨午晚检 resumexisu\n"
    logger.debug(ret_msgs)

    for msg in ret_msgs:
        print(msg)


def add_by_cookie(args: List[str]):
    if len(args) != 2:
        print(
            f"例：add_by_cookie `1cmgkrrcssge6edkkg3ucigj1m` `44f522350f5e843fbac58b726753eb36`"
        )
        return
    eaisess = args[0]
    uukey = args[1]
    print(f"Adding ...")

    buptuser, _ = BUPTUser.get_or_create(
        cookie_eaisess=eaisess,
        cookie_uukey=uukey,
        status=BUPTUserStatus.normal,
        xisu_checkin_status=BUPTUserStatus.normal,
    )

    print("添加成功！")
    list()


def add_by_uid(args: List[str]):
    if len(args) != 2:
        print(f"例：add_by_uid `2010211000` `password123`")
        return
    username = args[0]
    password = args[1]
    print(f"Adding ...")

    buptuser, _ = BUPTUser.get_or_create(
        username=username,
        password=password,
        status=BUPTUserStatus.normal,
        xisu_checkin_status=BUPTUserStatus.normal,
    )

    print("添加成功！")
    list()


def checkin(args: List[str]):
    if len(args) == 0:
        targets = get_buptusers()
    else:
        targets = get_users_by_seqids([int(i) for i in args])

    if len(targets) == 0:
        print("用户列表为空")
        return
    for buptuser in targets:
        try:
            ret = buptuser.ncov_checkin(force=True)[:100]
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n签到成功！\n服务器返回：`{ret}`"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n签到失败，服务器错误！\n`{e}`"
        except Exception as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n签到异常！\n服务器返回：`{e}`"
        print(ret_msg)


def checkinxisu(args: List[str]):
    if len(args) == 0:
        targets = get_buptusers()
    else:
        targets = get_users_by_seqids([int(i) for i in args])

    if len(targets) == 0:
        print("用户列表为空")
        return
    for buptuser in targets:
        try:
            ret = buptuser.xisu_ncov_checkin(force=True)[:100]
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n晨午晚检成功！\n服务器返回：`{ret}`"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n晨午晚检失败，服务器错误！\n`{e}`"
        except Exception as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n晨午晚检异常！\n服务器返回：`{e}`"
        print(ret_msg)


def pausexisu(args: List[str]):
    if len(args) == 0:
        targets = get_buptusers()
    else:
        targets = get_users_by_seqids([int(i) for i in args])

    for buptuser in targets:
        buptuser.xisu_checkin_status = BUPTUserStatus.stopped
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已暂停自动晨午晚检。"
        print(ret_msg)


def resumexisu(args: List[str]):
    if len(args) == 0:
        targets = get_buptusers()
    else:
        targets = get_users_by_seqids([int(i) for i in args])

    for buptuser in targets:
        buptuser.xisu_checkin_status = BUPTUserStatus.normal
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已启用自动晨午晚检。"
        print(ret_msg)


def pause(args: List[str]):
    if len(args) == 0:
        targets = get_buptusers()
    else:
        targets = get_users_by_seqids([int(i) for i in args])

    for buptuser in targets:
        buptuser.status = BUPTUserStatus.stopped
        buptuser.save()
        ret_msg = (
            f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已暂停自动签到。"
        )
        print(ret_msg)


def resume(args: List[str]):
    if len(args) == 0:
        targets = get_buptusers()
    else:
        targets = get_users_by_seqids([int(i) for i in args])

    for buptuser in targets:
        buptuser.status = BUPTUserStatus.normal
        buptuser.save()
        ret_msg = (
            f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已启用自动签到。"
        )
        print(ret_msg)


def remove(args: List[str]):
    assert len(args) > 0, "错误的命令，请用 help 查看使用帮助。"

    if args[0].lower() == "all":
        targets = get_buptusers()
    else:
        targets = get_users_by_seqids([int(i) for i in args])

    for buptuser in targets:
        buptuser.status = BUPTUserStatus.removed
        buptuser.save()
        ret_msg = (
            f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已删除。"
        )
        print(ret_msg)

    list()


def error_callback(error: Exception):
    global logger
    """Log Errors caused by Updates."""
    logger.warning(
        'Error "%s: %s"',
        error.__class__.__name__,
        error,
    )
    print("{}: {}".format(error.__class__.__name__, error))
    traceback.print_exc()


def status():
    cron_data = "\n".join(
        [
            "name: %s, trigger: %s, handler: %s, next: %s"
            % (job.name, job.trigger, job.func, job.next_run_time)
            for job in scheduler.get_jobs()
        ]
    )
    print("Cronjob:\n" + cron_data)
    print("System time:\n" + str(datetime.datetime.now()))


def backup_db():
    global logger
    logger.info("backup started!")
    copyfile(
        "./my_app.db",
        "./backup/my_app.{}.db".format(
            str(datetime.datetime.now()).replace(":", "").replace(" ", "_")
        ),
    )
    logger.info("backup finished!")


def checkin_all_retry():
    global logger
    logger.info("checkin_all_retry started!")
    for user in BUPTUser.select().where(
        (BUPTUser.status == BUPTUserStatus.normal)
        & (
            BUPTUser.latest_response_time
            < datetime.datetime.combine(
                datetime.date.today(), datetime.datetime.min.time()
            )
        )
    ):
        ret_msg = ""
        try:
            ret = user.ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试签到成功！\n服务器返回：`{ret}`\n{display_time_formatted()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试签到失败，服务器错误，请尝试手动签到！\nhttps://app.bupt.edu.cn/ncov/wap/default/index\n`{e}`\n{display_time_formatted()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试签到异常！\n服务器返回：`{e}`\n{display_time_formatted()}"
            traceback.print_exc()
        logger.info(ret_msg)
    logger.info("checkin_all_retry finished!")


def checkin_all():
    global logger
    try:
        backup_db()
    except:
        pass
    logger.info("checkin_all started!")
    for user in BUPTUser.select().where(BUPTUser.status == BUPTUserStatus.normal):
        ret_msg = ""
        try:
            ret = user.ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动签到成功！\n服务器返回：`{ret}`\n{display_time_formatted()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动签到失败，服务器错误，将重试！\n`{e}`\n{display_time_formatted()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动签到异常！\n服务器返回：`{e}`\n{display_time_formatted()}"
            traceback.print_exc()
        logger.info(ret_msg)
    logger.info("checkin_all finished!")


def checkin_all_xisu_retry():
    global logger
    logger.info("xisu_checkin_all_retry started!")
    for user in BUPTUser.select().where(
        (BUPTUser.status != BUPTUserStatus.removed)
        & (BUPTUser.xisu_checkin_status == BUPTUserStatus.normal)
        & (
            BUPTUser.latest_xisu_checkin_response_time
            < datetime.datetime.combine(
                datetime.date.today(), datetime.datetime.min.time()
            )
        )
    ):
        ret_msg = ""
        try:
            ret = user.xisu_ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试晨午晚检成功！\n服务器返回：`{ret}`\n{display_time_formatted()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试晨午晚检失败，服务器错误，请尝试手动签到！\n{config.XISU_REPORT_PAGE}\n`{e}`\n{display_time_formatted()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试晨午晚检异常！\n服务器返回：`{e}`\n{display_time_formatted()}"
            traceback.print_exc()
        logger.info(ret_msg)
    logger.info("xisu_checkin_all_retry finished!")


def checkin_all_xisu():
    global logger
    try:
        backup_db()
    except:
        pass
    logger.info("xisu_checkin_all started!")
    for user in BUPTUser.select().where(
        (BUPTUser.status != BUPTUserStatus.removed)
        & (BUPTUser.xisu_checkin_status == BUPTUserStatus.normal)
    ):
        ret_msg = ""
        try:
            ret = user.xisu_ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动晨午晚检成功！\n服务器返回：`{ret}`\n{display_time_formatted()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动晨午晚检失败，服务器错误，将重试！\n`{e}`\n{display_time_formatted()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动晨午晚检异常！\n服务器返回：`{e}`\n{display_time_formatted()}"
            traceback.print_exc()
        logger.info(ret_msg)
    logger.info("xisu_checkin_all finished!")


def help():
    print(HELP_MSG)


def cmdline():
    while True:
        try:
            iptstr = input()
            splitstrs = iptstr.split(sep=" ")
            command = splitstrs[0]
            args = splitstrs[1:]
            if command == "list":
                list()
            elif command == "add_by_cookie":
                add_by_cookie(args)
            elif command == "add_by_uid":
                add_by_uid(args)
            elif command == "checkin":
                checkin(args)
            elif command == "checkinxisu":
                checkinxisu(args)
            elif command == "pause":
                pause(args)
            elif command == "resume":
                resume(args)
            elif command == "pausexisu":
                pausexisu(args)
            elif command == "resumexisu":
                resumexisu(args)
            elif command == "remove":
                remove(args)
            elif command == "status":
                status()
            elif command == "backup_db":
                backup_db()
            elif command == "checkin_all":
                checkin_all()
            elif command == "checkinxisu_all":
                checkin_all_xisu()
            elif command == "help":
                help()
            else:
                print("错误的命令，请用 help 查看使用帮助。")
        except Exception as e:
            error_callback(e)


def exitgrace(signum, frame):
    print("Stop signal received, exiting...")
    scheduler.shutdown(wait=True)
    exit(0)


def main():
    global scheduler
    parser = argparse.ArgumentParser(description="BUPT 2019-nCoV Report Bot")
    parser.add_argument("--initdb", default=False, action="store_true")
    args = parser.parse_args()

    database = SqliteDatabase(config.SQLITE_DB_FILE_PATH)
    database_proxy.initialize(database)

    if args.initdb:
        db_init()
        exit(0)

    signal.signal(signal.SIGINT, exitgrace)
    signal.signal(signal.SIGTERM, exitgrace)
    signal.signal(signal.SIGABRT, exitgrace)

    scheduler.add_job(
        func=checkin_all,
        id="checkin_all",
        trigger="cron",
        hour=CHECKIN_ALL_CRON_HOUR,
        minute=CHECKIN_ALL_CRON_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )
    scheduler.add_job(
        func=checkin_all_retry,
        id="checkin_all_retry",
        trigger="cron",
        hour=CHECKIN_ALL_CRON_RETRY_HOUR,
        minute=CHECKIN_ALL_CRON_RETRY_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    # xisu checkin morning cron job group
    scheduler.add_job(
        func=checkin_all_xisu,
        id="xisu_checkin_all_morning",
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_MORNING_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_MORNING_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )
    scheduler.add_job(
        func=checkin_all_xisu_retry,
        id="xisu_checkin_all_morning_retry",
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_MORNING_RETRY_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_MORNING_RETRY_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    # xisu checkin noon cron job group
    scheduler.add_job(
        func=checkin_all_xisu,
        id="xisu_checkin_all_noon",
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_NOON_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_NOON_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )
    scheduler.add_job(
        func=checkin_all_xisu_retry,
        id="xisu_checkin_all_noon_retry",
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_NOON_RETRY_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_NOON_RETRY_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    # xisu checkin night cron job group
    scheduler.add_job(
        func=checkin_all_xisu,
        id="xisu_checkin_all_night",
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_NIGHT_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_NIGHT_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )
    scheduler.add_job(
        func=checkin_all_xisu_retry,
        id="xisu_checkin_all_night_retry",
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_NIGHT_RETRY_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_NIGHT_RETRY_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    scheduler.start()
    logger.info(
        [
            "name: %s, trigger: %s, handler: %s, next: %s"
            % (job.name, job.trigger, job.func, job.next_run_time)
            for job in scheduler.get_jobs()
        ]
    )

    cmdline()


if __name__ == "__main__":
    logging.basicConfig(
        handlers=[
            TimedRotatingFileHandler(
                "log/main.txt",
                when="midnight",
                backupCount=30,
                encoding="utf-8",
                atTime=datetime.time(hour=0, minute=0),
            ),
        ],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    scheduler = BackgroundScheduler(timezone=CRON_TIMEZONE)

    main()
